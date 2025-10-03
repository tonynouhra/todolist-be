"""AI service layer with Google Gemini integration."""

import asyncio
import json
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import google.generativeai as genai
from google.generativeai.types import HarmBlockThreshold, HarmCategory
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.exceptions.ai import (
    AIConfigurationError,
    AIContentFilterError,
    AIInvalidRequestError,
    AIParsingError,
    AIQuotaExceededError,
    AIRateLimitError,
    AIServiceError,
    AIServiceUnavailableError,
    AITimeoutError,
)
from app.schemas.ai import (
    AIServiceStatus,
    FileAnalysisRequest,
    FileAnalysisResponse,
    GeneratedSubtask,
    GeneratedTodo,
    SubtaskGenerationRequest,
    SubtaskGenerationResponse,
    TaskOptimizationRequest,
    TaskOptimizationResponse,
    TodoSuggestionRequest,
    TodoSuggestionResponse,
)
from models.ai_interaction import AIInteraction
from models.file import File
from models.todo import Todo


logger = logging.getLogger(__name__)


class AIService:
    """Service class for AI operations using Google Gemini."""

    def __init__(self, db: AsyncSession):
        """Initialize AI service with database session.

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
                    HarmCategory.HARM_CATEGORY_HARASSMENT: (
                        HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
                    ),
                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: (
                        HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
                    ),
                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: (
                        HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
                    ),
                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: (
                        HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
                    ),
                },
                generation_config=genai.types.GenerationConfig(
                    candidate_count=1,
                    max_output_tokens=settings.gemini_max_tokens,
                    temperature=0.7,
                ),
            )
            logger.info(f"Google Gemini client initialized successfully with model: {model_name}")

        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {str(e)}")
            # Try to list available models for debugging
            try:
                available_models = list(genai.list_models())
                logger.info(f"Available models: {[model.name for model in available_models]}")
            except Exception:
                logger.warning("Could not list available models")
            raise AIConfigurationError(f"Failed to initialize AI service: {str(e)}") from e

    async def generate_subtasks(
        self, request: SubtaskGenerationRequest, user_id: UUID
    ) -> SubtaskGenerationResponse:
        """Generate AI subtasks for an existing todo."""
        if not self.model:
            raise AIServiceUnavailableError("AI service not properly initialized")

        # Get the existing todo
        todo = await self._get_todo_by_id(request.todo_id, user_id)
        if not todo:
            raise AIInvalidRequestError("Todo not found or access denied")

        # Build the prompt using todo data
        prompt = self._build_subtask_generation_prompt_from_todo(
            todo, request.min_subtasks, request.max_subtasks
        )

        try:
            # Make the AI request with timeout
            response = await asyncio.wait_for(
                self._generate_content_async(prompt),
                timeout=settings.ai_request_timeout,
            )

            # Parse the response
            subtasks = self._parse_subtask_response(response)

            # Store the interaction
            await self._store_interaction(
                user_id=user_id,
                todo_id=todo.id,
                prompt=prompt,
                response=response,
                interaction_type="subtask_generation",
            )

            # Create subtask records in database
            for subtask_data in subtasks:
                subtask = Todo(
                    user_id=user_id,
                    project_id=todo.project_id,  # Inherit parent's project
                    parent_todo_id=todo.id,
                    title=subtask_data.title,
                    description=subtask_data.description,
                    status="todo",
                    priority=subtask_data.priority,
                    ai_generated=True,
                )

                self.db.add(subtask)

            # Commit all subtasks
            await self.db.commit()

            # Build response
            ai_response = SubtaskGenerationResponse(
                parent_task_title=todo.title,
                generated_subtasks=subtasks,
                total_subtasks=len(subtasks),
                generation_timestamp=datetime.now(UTC),
                ai_model=settings.gemini_model,
            )

            logger.info(f"Generated {len(subtasks)} subtasks for task: {todo.title}")
            return ai_response

        except TimeoutError:
            await self.db.rollback()
            raise AITimeoutError("AI request timed out") from None
        except json.JSONDecodeError as e:
            await self.db.rollback()
            raise AIParsingError(f"Failed to parse AI response: {str(e)}") from e
        except AIParsingError:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            error_msg = str(e).lower()
            if "rate" in error_msg and "limit" in error_msg:
                raise AIRateLimitError("Rate limit exceeded") from e
            elif "quota" in error_msg:
                raise AIQuotaExceededError("API quota exceeded") from e
            elif "safety" in error_msg or "blocked" in error_msg:
                raise AIContentFilterError("Content blocked by safety filters") from e
            else:
                logger.error(f"AI service error: {str(e)}")
                raise AIServiceError(f"AI service error: {str(e)}") from e

    async def analyze_file(
        self, request: FileAnalysisRequest, user_id: UUID
    ) -> FileAnalysisResponse:
        """Analyze a file using AI."""
        if not self.model:
            raise AIServiceUnavailableError("AI service not properly initialized")

        # Get file from database
        file = await self._get_file_by_id(request.file_id, user_id)
        if not file:
            raise AIInvalidRequestError("File not found or access denied")

        # Build analysis prompt based on file type and content
        prompt = self._build_file_analysis_prompt(file, request.analysis_type, request.context)

        try:
            response = await asyncio.wait_for(
                self._generate_content_async(prompt),
                timeout=settings.ai_request_timeout,
            )

            # Parse analysis response
            analysis_data = self._parse_file_analysis_response(response)

            # Store interaction
            await self._store_interaction(
                user_id=user_id,
                prompt=prompt,
                response=response,
                interaction_type="file_analysis",
            )

            return FileAnalysisResponse(
                file_id=request.file_id,
                analysis_type=request.analysis_type,
                summary=analysis_data["summary"],
                key_points=analysis_data.get("key_points", []),
                suggested_tasks=analysis_data.get("suggested_tasks", []),
                confidence_score=analysis_data.get("confidence", 0.8),
                analysis_timestamp=datetime.now(UTC),
                ai_model=settings.gemini_model,
            )

        except TimeoutError:
            raise AITimeoutError("File analysis request timed out") from None
        except json.JSONDecodeError as e:
            raise AIParsingError(f"Failed to parse AI response: {str(e)}") from e
        except Exception as e:
            error_msg = str(e).lower()
            if "rate" in error_msg and "limit" in error_msg:
                raise AIRateLimitError("Rate limit exceeded") from e
            elif "quota" in error_msg:
                raise AIQuotaExceededError("API quota exceeded") from e
            elif "safety" in error_msg or "blocked" in error_msg:
                raise AIContentFilterError("Content blocked by safety filters") from e
            else:
                logger.error(f"AI service error: {str(e)}")
                raise AIServiceError(f"AI service error: {str(e)}") from e

    async def suggest_todos(
        self, request: TodoSuggestionRequest, user_id: UUID
    ) -> TodoSuggestionResponse:
        """Generate AI todo suggestions based on user input."""
        if not self.model:
            raise AIServiceUnavailableError("AI service not properly initialized")

        # Build the prompt for todo suggestions
        prompt = self._build_todo_suggestion_prompt(request)

        try:
            response = await asyncio.wait_for(
                self._generate_content_async(prompt),
                timeout=settings.ai_request_timeout,
            )

            # Parse the response
            todo_suggestions = self._parse_todo_suggestion_response(response)

            # Store the interaction
            await self._store_interaction(
                user_id=user_id,
                prompt=prompt,
                response=response,
                interaction_type="todo_suggestion",
            )

            ai_response = TodoSuggestionResponse(
                request_description=request.user_input,
                generated_todos=todo_suggestions,
                total_todos=len(todo_suggestions),
                generation_timestamp=datetime.now(UTC),
                ai_model=settings.gemini_model,
            )

            logger.info(f"Generated {len(todo_suggestions)} todo suggestions")
            return ai_response

        except TimeoutError:
            raise AITimeoutError("Todo suggestion request timed out") from None
        except json.JSONDecodeError as e:
            raise AIParsingError(f"Failed to parse AI response: {str(e)}") from e
        except Exception as e:
            error_msg = str(e).lower()
            if "rate" in error_msg and "limit" in error_msg:
                raise AIRateLimitError("Rate limit exceeded") from e
            elif "quota" in error_msg:
                raise AIQuotaExceededError("API quota exceeded") from e
            elif "safety" in error_msg or "blocked" in error_msg:
                raise AIContentFilterError("Content blocked by safety filters") from e
            else:
                logger.error(f"AI service error: {str(e)}")
                raise AIServiceError(f"AI service error: {str(e)}") from e

    async def optimize_task(
        self, request: TaskOptimizationRequest, user_id: UUID
    ) -> TaskOptimizationResponse:
        """Optimize an existing task title and/or description using AI."""
        if not self.model:
            raise AIServiceUnavailableError("AI service not properly initialized")

        # If todo_id is provided, get the current todo data
        if request.todo_id:
            todo = await self._get_todo_by_id(request.todo_id, user_id)
            if not todo:
                raise AIInvalidRequestError("Todo not found or access denied")

            # Use todo data if not provided in request
            current_title = request.current_title or todo.title
            current_description = request.current_description or todo.description
        else:
            current_title = request.current_title
            current_description = request.current_description

        if not current_title and not current_description:
            raise AIInvalidRequestError(
                "Either todo_id or current_title/description must be provided"
            )

        # Build the optimization prompt
        prompt = self._build_task_optimization_prompt(
            current_title, current_description, request.optimization_type, request.context
        )

        try:
            response = await asyncio.wait_for(
                self._generate_content_async(prompt),
                timeout=settings.ai_request_timeout,
            )

            # Parse the response
            optimization_data = self._parse_task_optimization_response(response)

            # Store the interaction
            await self._store_interaction(
                user_id=user_id,
                todo_id=request.todo_id,
                prompt=prompt,
                response=response,
                interaction_type="task_optimization",
            )

            ai_response = TaskOptimizationResponse(
                original_title=current_title,
                original_description=current_description,
                optimized_title=optimization_data.get("optimized_title"),
                optimized_description=optimization_data.get("optimized_description"),
                optimization_type=request.optimization_type,
                improvements=optimization_data.get("improvements", []),
                optimization_timestamp=datetime.now(UTC),
                ai_model=settings.gemini_model,
            )

            logger.info(f"Optimized task: {current_title[:50]}...")
            return ai_response

        except TimeoutError:
            raise AITimeoutError("Task optimization request timed out") from None
        except json.JSONDecodeError as e:
            raise AIParsingError(f"Failed to parse AI response: {str(e)}") from e
        except Exception as e:
            error_msg = str(e).lower()
            if "rate" in error_msg and "limit" in error_msg:
                raise AIRateLimitError("Rate limit exceeded") from e
            elif "quota" in error_msg:
                raise AIQuotaExceededError("API quota exceeded") from e
            elif "safety" in error_msg or "blocked" in error_msg:
                raise AIContentFilterError("Content blocked by safety filters") from e
            else:
                logger.error(f"AI service error: {str(e)}")
                raise AIServiceError(f"AI service error: {str(e)}") from e

    async def get_service_status(self) -> AIServiceStatus:
        """Get AI service status and usage information."""
        service_available = False
        actual_model_name = settings.gemini_model
        requests_today = 0

        try:
            # Get today's interaction count first (this should always work)
            today = datetime.now(UTC).date()
            query = select(AIInteraction).where(AIInteraction.created_at >= today)
            result = await self.db.execute(query)
            requests_today = len(result.scalars().all())

            # Check if AI service is configured
            if not settings.gemini_api_key:
                logger.warning("AI service not configured - no API key")
                return AIServiceStatus(
                    service_available=False,
                    model_name="not_configured",
                    last_request_timestamp=None,
                    requests_today=requests_today,
                )

            # Check if model is initialized
            if not self.model:
                logger.warning("AI model not initialized")
                return AIServiceStatus(
                    service_available=False,
                    model_name=actual_model_name,
                    last_request_timestamp=None,
                    requests_today=requests_today,
                )

            # Test service availability with a simple request
            test_prompt = "Respond with 'OK' if you can process this request."
            response = await asyncio.wait_for(
                self._generate_content_async(test_prompt), timeout=5.0
            )

            service_available = "ok" in response.lower()

            return AIServiceStatus(
                service_available=service_available,
                model_name=actual_model_name,
                last_request_timestamp=datetime.now(UTC),
                requests_today=requests_today,
            )

        except TimeoutError:
            logger.error("Service status check timed out")
        except Exception as e:
            logger.error(f"Service status check failed: {str(e)}")

        # Return failed status
        return AIServiceStatus(
            service_available=False,
            model_name=actual_model_name,
            last_request_timestamp=None,
            requests_today=requests_today,
        )

    # Private helper methods

    def _build_subtask_generation_prompt_from_todo(
        self, todo: Todo, min_subtasks: int, max_subtasks: int
    ) -> str:
        """Build prompt for subtask generation from todo data."""
        base_prompt = f"""
Given the following main task, generate a list of specific,
actionable subtasks that would help complete it efficiently.

**Main Task:** {todo.title}
"""

        if todo.description:
            base_prompt += f"**Description:** {todo.description}\n"

        if todo.priority:
            priority_text = ["very low", "low", "medium", "high", "very high"][todo.priority - 1]
            base_prompt += f"**Priority Level:** {priority_text}\n"

        if todo.due_date:
            base_prompt += f"**Due Date:** {todo.due_date.strftime('%Y-%m-%d')}\n"

        base_prompt += f"""
**Requirements:**
1. Generate between {min_subtasks} and {max_subtasks} subtasks
2. Each subtask should be specific and actionable
3. Order them logically for efficient completion
4. Include estimated time where relevant
5. Make sure subtasks are not too granular or too broad

**Response Format (JSON only):**
```json
{{
    "subtasks": [
        {{
            "title": "Subtask title (under 100 characters)",
            "description": "Brief description if needed (optional)",
            "priority": 3,
            "estimated_time": "30 minutes",
            "order": 1
        }}
    ]
}}
```

Generate practical, actionable subtasks that break down the main task effectively:
"""

        return base_prompt

    def _build_file_analysis_prompt(
        self, file: File, analysis_type: str, context: str | None
    ) -> str:
        """Build prompt for file analysis."""
        prompt = f"""
Analyze the following file and provide insights based on the analysis type requested.

**File Information:**
- Name: {file.filename}
- Type: {file.content_type}
- Size: {file.file_size} bytes
- Analysis Type: {analysis_type}
"""

        if context:
            prompt += f"**Additional Context:** {context}\n"

        if analysis_type == "task_extraction":
            prompt += """
**Task:** Extract actionable tasks, todos, or action items from this file.

**Response Format (JSON):**
```json
{
    "summary": "Brief summary of the file content",
    "key_points": ["Important point 1", "Important point 2"],
    "suggested_tasks": ["Task 1", "Task 2", "Task 3"],
    "confidence": 0.85
}
```
"""
        elif analysis_type == "summary":
            prompt += """
**Task:** Provide a comprehensive summary of the file content.

**Response Format (JSON):**
```json
{
    "summary": "Detailed summary of the content",
    "key_points": ["Main point 1", "Main point 2", "Main point 3"],
    "suggested_tasks": [],
    "confidence": 0.90
}
```
"""
        else:  # general
            prompt += """
**Task:** Provide a general analysis of the file content
including key insights and potential action items.

**Response Format (JSON):**
```json
{
    "summary": "General analysis and overview",
    "key_points": ["Key insight 1", "Key insight 2"],
    "suggested_tasks": ["Suggested action 1", "Suggested action 2"],
    "confidence": 0.80
}
```
"""

        # Note: In a real implementation, you'd need to include the actual file content
        # This might require additional logic to extract text from different file types
        prompt += "\n**File Content:** [File content would be inserted here based on file type]"

        return prompt

    def _build_todo_suggestion_prompt(self, request: TodoSuggestionRequest) -> str:
        """Build prompt for AI todo suggestions."""
        prompt = f"""
Generate a list of actionable todo items based on the user's input.

**User Request:** {request.user_input}
"""

        if request.project_id:
            prompt += (
                f"**Project Context:** This is for a specific project (ID: {request.project_id})\n"
            )

        if request.existing_todos:
            existing_list = "\n".join([f"- {todo}" for todo in request.existing_todos[:10]])
            prompt += f"""
**Existing Todos for Context:**
{existing_list}
"""

        prompt += f"""
**Requirements:**
1. Generate between 1 and {request.max_todos} relevant todos
2. Make each todo specific and actionable
3. Consider the user's existing todos to avoid duplicates
4. Include realistic time estimates where appropriate
5. Assign appropriate priority levels (1=very low, 5=very high)
6. Suggest categories if relevant

**Response Format (JSON only):**
```json
{{
    "todos": [
        {{
            "title": "Todo title (under 500 characters)",
            "description": "Brief description if needed (optional)",
            "priority": 3,
            "estimated_time": "30 minutes",
            "category": "category name"
        }}
    ]
}}
```

Generate practical, actionable todos that help the user accomplish their goal:
"""

        return prompt

    def _build_task_optimization_prompt(
        self,
        title: str | None,
        description: str | None,
        optimization_type: str,
        context: str | None,
    ) -> str:
        """Build prompt for task optimization."""
        prompt = """
Optimize the following task to make it clearer, more actionable, and better organized.

**Current Task:**
"""

        if title:
            prompt += f"Title: {title}\n"
        if description:
            prompt += f"Description: {description}\n"

        prompt += f"""
**Optimization Type:** {optimization_type}
"""

        if context:
            prompt += f"**Additional Context:** {context}\n"

        if optimization_type == "title":
            prompt += """
**Task:** Improve only the task title to be more clear and actionable.

**Response Format (JSON):**
```json
{
    "optimized_title": "Improved title text",
    "improvements": ["List of specific improvements made"]
}
```
"""
        elif optimization_type == "description":
            prompt += """
**Task:** Improve only the task description to be more detailed and actionable.

**Response Format (JSON):**
```json
{
    "optimized_description": "Improved description with more detail and clarity",
    "improvements": ["List of specific improvements made"]
}
```
"""
        elif optimization_type == "both":
            prompt += """
**Task:** Improve both the title and description for maximum clarity and actionability.

**Response Format (JSON):**
```json
{
    "optimized_title": "Improved title text",
    "optimized_description": "Improved description with more detail",
    "improvements": ["List of specific improvements made"]
}
```
"""
        elif optimization_type == "clarity":
            prompt += """
**Task:** Focus on making the task clearer and easier to understand.

**Response Format (JSON):**
```json
{
    "optimized_title": "Clearer title if needed",
    "optimized_description": "Clearer description if needed",
    "improvements": ["List of clarity improvements made"]
}
```
"""
        else:  # detail
            prompt += """
**Task:** Add more helpful detail while keeping the task focused.

**Response Format (JSON):**
```json
{
    "optimized_title": "More detailed title if needed",
    "optimized_description": "More detailed description with specific steps",
    "improvements": ["List of detail improvements made"]
}
```
"""

        prompt += """
Make the task more actionable and well-defined:
"""

        return prompt

    async def _generate_content_async(self, prompt: str) -> str:
        """Generate content using Gemini API asynchronously."""
        try:
            # Run the synchronous Gemini API call in a thread pool
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: self.model.generate_content(prompt))

            if not response or not response.text:
                raise AIServiceError("Empty response from AI service")

            return response.text

        except Exception as e:
            logger.error(f"Gemini API call failed: {str(e)}")
            raise AIServiceError(f"AI generation failed: {str(e)}") from e

    def _parse_subtask_response(self, response: str) -> list[GeneratedSubtask]:
        """Parse AI response into structured subtasks."""
        try:
            # Extract JSON from response (handle code blocks)
            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start == -1 or json_end == 0:
                raise AIParsingError("No JSON found in response")

            json_str = response[json_start:json_end]
            data = json.loads(json_str)

            subtasks = []
            for idx, subtask_data in enumerate(data.get("subtasks", []), 1):
                subtask = GeneratedSubtask(
                    title=subtask_data.get("title", f"Subtask {idx}"),
                    description=subtask_data.get("description"),
                    priority=subtask_data.get("priority", 3),
                    estimated_time=subtask_data.get("estimated_time"),
                    order=subtask_data.get("order", idx),
                )
                subtasks.append(subtask)

            return subtasks

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse subtask JSON: {str(e)}")
            raise AIParsingError(f"Invalid JSON response: {str(e)}") from e
        except Exception as e:
            logger.error(f"Error parsing subtask response: {str(e)}")
            raise AIParsingError(f"Failed to parse response: {str(e)}") from e

    def _parse_file_analysis_response(self, response: str) -> dict[str, Any]:
        """Parse AI file analysis response."""
        try:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start == -1 or json_end == 0:
                raise AIParsingError("No JSON found in analysis response")

            json_str = response[json_start:json_end]
            return json.loads(json_str)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse analysis JSON: {str(e)}")
            raise AIParsingError(f"Invalid JSON in analysis response: {str(e)}") from e

    def _parse_todo_suggestion_response(self, response: str) -> list[GeneratedTodo]:
        """Parse AI response into structured todo suggestions."""
        try:
            # Extract JSON from response (handle code blocks)
            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start == -1 or json_end == 0:
                raise AIParsingError("No JSON found in todo suggestion response")

            json_str = response[json_start:json_end]
            data = json.loads(json_str)

            todos = []
            for idx, todo_data in enumerate(data.get("todos", []), 1):
                todo = GeneratedTodo(
                    title=todo_data.get("title", f"Generated Todo {idx}"),
                    description=todo_data.get("description"),
                    priority=todo_data.get("priority", 3),
                    estimated_time=todo_data.get("estimated_time"),
                    category=todo_data.get("category"),
                )
                todos.append(todo)

            return todos

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse todo suggestion JSON: {str(e)}")
            raise AIParsingError(f"Invalid JSON response: {str(e)}") from e
        except Exception as e:
            logger.error(f"Error parsing todo suggestion response: {str(e)}")
            raise AIParsingError(f"Failed to parse response: {str(e)}") from e

    def _parse_task_optimization_response(self, response: str) -> dict[str, Any]:
        """Parse AI task optimization response."""
        try:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start == -1 or json_end == 0:
                raise AIParsingError("No JSON found in optimization response")

            json_str = response[json_start:json_end]
            data = json.loads(json_str)

            # Ensure improvements is a list
            if "improvements" in data and not isinstance(data["improvements"], list):
                data["improvements"] = [str(data["improvements"])]

            return data

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse optimization JSON: {str(e)}")
            raise AIParsingError(f"Invalid JSON in optimization response: {str(e)}") from e

    async def _store_interaction(
        self,
        user_id: UUID,
        prompt: str,
        response: str,
        interaction_type: str,
        todo_id: UUID | None = None,
    ) -> None:
        """Store AI interaction in database."""
        try:
            interaction = AIInteraction(
                user_id=user_id,
                todo_id=todo_id,
                prompt=prompt,
                response=response,
                interaction_type=interaction_type,
            )

            self.db.add(interaction)
            await self.db.commit()

        except SQLAlchemyError as e:
            logger.error(f"Failed to store AI interaction: {str(e)}")
            await self.db.rollback()
            # Don't raise here - interaction storage failure shouldn't fail the main operation

    async def _get_file_by_id(self, file_id: UUID, user_id: UUID) -> File | None:
        """Get file by ID and verify user ownership."""
        query = select(File).where(File.id == file_id, File.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _get_todo_by_id(self, todo_id: UUID, user_id: UUID) -> Todo | None:
        """Get todo by ID and verify user ownership."""
        query = select(Todo).where(Todo.id == todo_id, Todo.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    def _get_available_model(self) -> str:
        """Get the first available model that supports generateContent."""
        try:
            # First try the configured model
            available_models = list(genai.list_models())
            model_names = [
                model.name
                for model in available_models
                if "generateContent" in model.supported_generation_methods
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
            # Last resort: return the configured model and let it fail with a clear error
            return settings.gemini_model
