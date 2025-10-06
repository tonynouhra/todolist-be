"""Chat service layer with AI assistant integration."""

import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import google.generativeai as genai
from google.generativeai.types import HarmBlockThreshold, HarmCategory
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.exceptions.ai import (
    AIConfigurationError,
    AIServiceError,
    AITimeoutError,
)
from app.schemas.chat import (
    ChatAction,
    ChatConversationDetailResponse,
    ChatConversationResponse,
    ChatHistoryResponse,
    ChatMessageResponse,
    ChatRequest,
    ChatResponse,
    MessageRole,
)
from models.chat_conversation import ChatConversation
from models.chat_message import ChatMessage
from models.project import Project
from models.todo import Todo


logger = logging.getLogger(__name__)


class ChatService:
    """Service class for AI chat operations using Google Gemini."""

    def __init__(self, db: AsyncSession):
        """Initialize chat service with database session.

        Args:
            db: Async database session for data operations.
        """
        self.db = db
        self.model = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Google Gemini client."""
        if not settings.gemini_api_key:
            raise AIConfigurationError("Gemini API key not configured")

        try:
            genai.configure(api_key=settings.gemini_api_key)

            # Get the correct model name
            model_name = self._get_available_model()

            # Configure the model with safety settings
            self.model = genai.GenerativeModel(
                model_name=model_name,
                safety_settings={
                    HarmCategory.HARM_CATEGORY_HARASSMENT: (HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: (HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: (HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: (HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE),
                },
                generation_config=genai.types.GenerationConfig(
                    candidate_count=1,
                    max_output_tokens=settings.gemini_max_tokens,
                    temperature=0.8,  # Slightly higher for conversational responses
                ),
            )
            logger.info(f"Chat Gemini client initialized successfully with model: {model_name}")

        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {str(e)}")
            raise AIConfigurationError(f"Failed to initialize AI service: {str(e)}") from e

    async def send_message(self, request: ChatRequest, user_id: UUID) -> ChatResponse:
        """Send a message and get AI response with possible actions.

        Args:
            request: Chat request with message and context
            user_id: User ID sending the message

        Returns:
            ChatResponse with user message, AI response, and any actions taken
        """
        if not self.model:
            raise AIConfigurationError("AI service not properly initialized")

        # Get or create conversation
        conversation = await self._get_or_create_conversation(request.conversation_id, user_id)

        # Store user message
        user_message = ChatMessage(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=request.message,
        )
        self.db.add(user_message)
        await self.db.flush()

        try:
            # Get conversation history for context
            history = await self._get_conversation_history(conversation.id)

            # Build prompt with context
            prompt = self._build_chat_prompt(request.message, history, request.context, user_id)

            # Get AI response
            response_text = await asyncio.wait_for(
                self._generate_content_async(prompt), timeout=settings.ai_request_timeout
            )

            # Parse response for actions
            parsed_response = self._parse_chat_response(response_text)

            # Execute suggested actions if confirmed
            actions_taken = []
            if parsed_response.get("suggested_actions"):
                for action_data in parsed_response["suggested_actions"]:
                    if not action_data.get("confirmation_required", True):
                        # Auto-execute actions that don't need confirmation
                        action_result = await self._execute_action(action_data, user_id, conversation.id)
                        actions_taken.append(action_result)

            # Store assistant message with actions
            assistant_message = ChatMessage(
                conversation_id=conversation.id,
                role=MessageRole.ASSISTANT,
                content=parsed_response.get("message", response_text),
                actions=[action.model_dump() for action in actions_taken] if actions_taken else None,
                has_actions=len(actions_taken) > 0,
            )
            self.db.add(assistant_message)

            # Update conversation title if first exchange
            if not conversation.title:
                conversation.title = self._generate_conversation_title(request.message)

            await self.db.commit()
            await self.db.refresh(user_message)
            await self.db.refresh(assistant_message)

            return ChatResponse(
                conversation_id=conversation.id,
                user_message=ChatMessageResponse.model_validate(user_message),
                assistant_message=ChatMessageResponse.model_validate(assistant_message),
                actions_taken=actions_taken,
                timestamp=datetime.now(UTC),
            )

        except TimeoutError:
            await self.db.rollback()
            raise AITimeoutError("Chat request timed out") from None
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Chat service error: {str(e)}")
            raise AIServiceError(f"Chat service error: {str(e)}") from e

    async def get_conversation_history(self, conversation_id: UUID, user_id: UUID) -> ChatConversationDetailResponse:
        """Get conversation with all messages.

        Args:
            conversation_id: Conversation ID
            user_id: User ID for authorization

        Returns:
            Conversation with messages
        """
        query = select(ChatConversation).where(
            ChatConversation.id == conversation_id, ChatConversation.user_id == user_id
        )
        result = await self.db.execute(query)
        conversation = result.scalar_one_or_none()

        if not conversation:
            raise ValueError("Conversation not found")

        # Get messages
        messages_query = (
            select(ChatMessage).where(ChatMessage.conversation_id == conversation_id).order_by(ChatMessage.created_at)
        )
        messages_result = await self.db.execute(messages_query)
        messages = messages_result.scalars().all()

        return ChatConversationDetailResponse(
            id=conversation.id,
            user_id=conversation.user_id,
            title=conversation.title,
            summary=conversation.summary,
            message_count=len(messages),
            messages=[ChatMessageResponse.model_validate(msg) for msg in messages],
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
        )

    async def get_user_conversations(self, user_id: UUID, page: int = 1, size: int = 20) -> ChatHistoryResponse:
        """Get all conversations for a user.

        Args:
            user_id: User ID
            page: Page number
            size: Page size

        Returns:
            List of conversations with pagination
        """
        offset = (page - 1) * size

        # Get total count
        count_query = select(func.count(ChatConversation.id)).where(ChatConversation.user_id == user_id)
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Get conversations
        query = (
            select(ChatConversation)
            .where(ChatConversation.user_id == user_id)
            .order_by(ChatConversation.updated_at.desc())
            .limit(size)
            .offset(offset)
        )
        result = await self.db.execute(query)
        conversations = result.scalars().all()

        # Get message counts
        conversation_responses = []
        for conv in conversations:
            msg_count_query = select(func.count(ChatMessage.id)).where(ChatMessage.conversation_id == conv.id)
            msg_count_result = await self.db.execute(msg_count_query)
            msg_count = msg_count_result.scalar() or 0

            conv_response = ChatConversationResponse(
                id=conv.id,
                user_id=conv.user_id,
                title=conv.title,
                summary=conv.summary,
                message_count=msg_count,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
            )
            conversation_responses.append(conv_response)

        return ChatHistoryResponse(
            conversations=conversation_responses,
            total=total,
            page=page,
            size=size,
            has_next=offset + size < total,
            has_prev=page > 1,
        )

    async def delete_conversation(self, conversation_id: UUID, user_id: UUID) -> bool:
        """Delete a conversation.

        Args:
            conversation_id: Conversation ID
            user_id: User ID for authorization

        Returns:
            True if deleted successfully
        """
        query = select(ChatConversation).where(
            ChatConversation.id == conversation_id, ChatConversation.user_id == user_id
        )
        result = await self.db.execute(query)
        conversation = result.scalar_one_or_none()

        if not conversation:
            raise ValueError("Conversation not found")

        await self.db.delete(conversation)
        await self.db.commit()
        return True

    # Private helper methods

    async def _get_or_create_conversation(self, conversation_id: UUID | None, user_id: UUID) -> ChatConversation:
        """Get existing conversation or create new one."""
        if conversation_id:
            query = select(ChatConversation).where(
                ChatConversation.id == conversation_id, ChatConversation.user_id == user_id
            )
            result = await self.db.execute(query)
            conversation = result.scalar_one_or_none()

            if not conversation:
                raise ValueError("Conversation not found")

            return conversation

        # Create new conversation
        conversation = ChatConversation(user_id=user_id)
        self.db.add(conversation)
        await self.db.flush()
        return conversation

    async def _get_conversation_history(self, conversation_id: UUID) -> list[dict]:
        """Get conversation message history."""
        query = (
            select(ChatMessage).where(ChatMessage.conversation_id == conversation_id).order_by(ChatMessage.created_at)
        )
        result = await self.db.execute(query)
        messages = result.scalars().all()

        return [{"role": msg.role.value, "content": msg.content} for msg in messages]

    def _build_chat_prompt(self, message: str, history: list[dict], context: dict | None, _user_id: UUID) -> str:
        """Build chat prompt with context and history."""
        system_prompt = """You are an AI assistant helping users manage their tasks and projects.

Your capabilities:
1. Answer questions about task management and productivity
2. Suggest projects, tasks, and subtasks based on user goals
3. Help users break down complex goals into actionable steps
4. Provide learning paths and development roadmaps

When suggesting tasks or projects:
- Be specific and actionable
- Consider the user's skill level and goals
- Break down complex topics into manageable steps
- Provide realistic time estimates where appropriate
- Assign appropriate priority levels (1=very low, 5=very high)

Response Format:
Always respond in JSON format with this structure:
```json
{
    "message": "Your conversational response to the user",
    "suggested_actions": [
        {
            "action_type": "create_project|create_task|create_subtasks",
            "title": "Title of project/task",
            "description": "Description",
            "priority": 3,
            "additional_data": {
                "subtasks": [...],  // For create_subtasks
                "estimated_time": "2 weeks",
                "category": "learning"
            },
            "confirmation_required": true
        }
    ]
}
```

Examples:
User: "What should I learn as a developer?"
Response with suggestions for popular languages and ask about their interests.

User: "I want to learn Python"
Response with a learning path and suggest creating a project with tasks for each learning phase.

User: "Create the Python learning project"
Execute the action to create the project with all suggested tasks.
"""

        # Add context if provided
        if context:
            system_prompt += f"\n\nCurrent Context:\n{json.dumps(context, indent=2)}"

        # Build conversation history
        conversation = system_prompt + "\n\nConversation:\n"
        for msg in history[-10:]:  # Last 10 messages for context
            conversation += f"{msg['role'].upper()}: {msg['content']}\n"

        conversation += f"USER: {message}\nASSISTANT:"

        return conversation

    async def _generate_content_async(self, prompt: str) -> str:
        """Generate content using Gemini API asynchronously."""
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: self.model.generate_content(prompt))

            if not response or not response.text:
                raise AIServiceError("Empty response from AI service")

            return response.text

        except Exception as e:
            logger.error(f"Gemini API call failed: {str(e)}")
            raise AIServiceError(f"AI generation failed: {str(e)}") from e

    def _parse_chat_response(self, response: str) -> dict[str, Any]:
        """Parse AI chat response."""
        try:
            # Extract JSON from response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start == -1 or json_end == 0:
                # No JSON found, treat as plain message
                return {"message": response, "suggested_actions": []}

            json_str = response[json_start:json_end]
            data = json.loads(json_str)

            return {
                "message": data.get("message", response),
                "suggested_actions": data.get("suggested_actions", []),
            }

        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse chat JSON, using raw response: {str(e)}")
            return {"message": response, "suggested_actions": []}

    async def _execute_action(self, action_data: dict, user_id: UUID, _conversation_id: UUID) -> ChatAction:
        """Execute an AI-suggested action.

        Args:
            action_data: Action data from AI response
            user_id: User ID
            _conversation_id: Conversation ID (reserved for future use)

        Returns:
            ChatAction with execution result
        """
        action_type = action_data.get("action_type")
        success = False
        error_message = None
        result_data = {}

        try:
            if action_type == "create_project":
                project = Project(
                    user_id=user_id,
                    name=action_data.get("title"),
                    description=action_data.get("description"),
                    color=action_data.get("additional_data", {}).get("color", "#2196F3"),
                )
                self.db.add(project)
                await self.db.flush()
                result_data = {"project_id": str(project.id), "name": project.name}
                success = True

            elif action_type == "create_task":
                task = Todo(
                    user_id=user_id,
                    title=action_data.get("title"),
                    description=action_data.get("description"),
                    priority=action_data.get("priority", 3),
                    ai_generated=True,
                )
                self.db.add(task)
                await self.db.flush()
                result_data = {"task_id": str(task.id), "title": task.title}
                success = True

            elif action_type == "create_subtasks":
                parent_task_id = action_data.get("additional_data", {}).get("parent_task_id")
                subtasks_data = action_data.get("additional_data", {}).get("subtasks", [])

                created_subtasks = []
                for subtask_data in subtasks_data:
                    subtask = Todo(
                        user_id=user_id,
                        parent_todo_id=parent_task_id,
                        title=subtask_data.get("title"),
                        description=subtask_data.get("description"),
                        priority=subtask_data.get("priority", 3),
                        ai_generated=True,
                    )
                    self.db.add(subtask)
                    await self.db.flush()
                    created_subtasks.append({"id": str(subtask.id), "title": subtask.title})

                result_data = {"subtasks": created_subtasks}
                success = True

            else:
                error_message = f"Unknown action type: {action_type}"

        except Exception as e:
            logger.error(f"Failed to execute action {action_type}: {str(e)}")
            error_message = str(e)

        return ChatAction(
            action_type=action_type,
            data={**action_data, "result": result_data},
            success=success,
            error_message=error_message,
        )

    def _generate_conversation_title(self, first_message: str) -> str:
        """Generate conversation title from first message."""
        # Simple title generation - take first 50 chars
        title = first_message[:50]
        if len(first_message) > 50:
            title += "..."
        return title

    def _get_available_model(self) -> str:
        """Get the first available model that supports generateContent."""
        try:
            available_models = list(genai.list_models())
            model_names = [
                model.name for model in available_models if "generateContent" in model.supported_generation_methods
            ]

            logger.info(f"Available models with generateContent: {model_names}")

            # Try to find the configured model first
            configured_model = settings.gemini_model
            for model_name in model_names:
                if configured_model in model_name or model_name.endswith(configured_model):
                    logger.info(f"Using configured model: {model_name}")
                    return model_name

            # Fall back to common model names
            preferred_models = [
                "gemini-1.5-flash",
                "gemini-1.5-pro",
                "gemini-pro",
                "models/gemini-1.5-flash",
                "models/gemini-1.5-pro",
                "models/gemini-pro",
            ]

            for preferred in preferred_models:
                for available in model_names:
                    if preferred in available or available.endswith(preferred.split("/")[-1]):
                        logger.info(f"Using fallback model: {available}")
                        return available

            # If no preferred model found, use the first available
            if model_names:
                logger.warning(f"Using first available model: {model_names[0]}")
                return model_names[0]

            raise AIConfigurationError("No models with generateContent support found")

        except Exception as e:
            logger.error(f"Failed to get available models: {str(e)}")
            return settings.gemini_model
