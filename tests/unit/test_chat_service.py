"""Unit tests for Chat Service."""

import json
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.chat.service import ChatService
from app.exceptions.ai import AIConfigurationError, AIServiceError, AITimeoutError
from app.schemas.chat import ChatRequest, MessageRole
from models.chat_conversation import ChatConversation
from models.chat_message import ChatMessage
from models.project import Project
from models.todo import Todo


@pytest.mark.asyncio
class TestChatService:
    """Test cases for ChatService."""

    @pytest.fixture
    def mock_genai(self):
        """Mock google.generativeai module."""
        with patch("app.domains.chat.service.genai") as mock:
            mock_model = MagicMock()
            mock_model.generate_content_async = AsyncMock()
            mock.GenerativeModel.return_value = mock_model

            # Mock list_models
            mock_model_obj = MagicMock()
            mock_model_obj.name = "models/gemini-1.5-flash-001"
            mock_model_obj.supported_generation_methods = ["generateContent"]
            mock.list_models.return_value = [mock_model_obj]

            yield mock

    @pytest.fixture
    async def chat_service(self, test_db: AsyncSession, mock_genai):
        """Create chat service instance."""
        with patch("app.core.config.settings.gemini_api_key", "test_api_key"):
            service = ChatService(test_db)
            yield service

    async def test_initialize_client_success(self, test_db: AsyncSession, mock_genai):
        """Test successful Gemini client initialization."""
        with patch("app.core.config.settings.gemini_api_key", "test_api_key"):
            service = ChatService(test_db)
            assert service.model is not None

    async def test_initialize_client_no_api_key(self, test_db: AsyncSession):
        """Test initialization fails without API key."""
        with patch("app.core.config.settings.gemini_api_key", None):
            with pytest.raises(AIConfigurationError) as exc_info:
                ChatService(test_db)
            assert "API key not configured" in str(exc_info.value)

    async def test_send_message_simple(
        self, chat_service: ChatService, test_user, mock_genai
    ):
        """Test sending a simple message without actions."""
        # Mock AI response
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "response": "Hello! How can I help you today?",
            "actions": []
        })
        chat_service.model.generate_content_async.return_value = mock_response

        # Send message
        request = ChatRequest(message="Hello")
        response = await chat_service.send_message(request, test_user.id)

        assert response.user_message == "Hello"
        assert "Hello! How can I help you today?" in response.ai_response
        assert len(response.actions) == 0
        assert response.conversation_id is not None

    async def test_send_message_create_project(
        self, chat_service: ChatService, test_user, mock_genai
    ):
        """Test sending a message that creates a project."""
        # Mock AI response with project creation action
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "response": "I've created a new project called 'My New Project' for you!",
            "actions": [
                {
                    "type": "create_project",
                    "data": {
                        "name": "My New Project",
                        "description": "A test project"
                    }
                }
            ]
        })
        chat_service.model.generate_content_async.return_value = mock_response

        # Send message
        request = ChatRequest(message="Create a project called My New Project")
        response = await chat_service.send_message(request, test_user.id)

        assert response.user_message == "Create a project called My New Project"
        assert "created" in response.ai_response.lower()
        assert len(response.actions) == 1
        assert response.actions[0].action_type == "create_project"

    async def test_send_message_create_todo(
        self, chat_service: ChatService, test_user, test_project, mock_genai
    ):
        """Test sending a message that creates a todo."""
        # Mock AI response with todo creation action
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "response": "I've created a new task for you!",
            "actions": [
                {
                    "type": "create_todo",
                    "data": {
                        "title": "Complete the report",
                        "description": "Finish the quarterly report",
                        "priority": 4,
                        "project_id": str(test_project.id)
                    }
                }
            ]
        })
        chat_service.model.generate_content_async.return_value = mock_response

        # Send message
        request = ChatRequest(
            message="Add a task to complete the quarterly report",
            context={"project_id": str(test_project.id)}
        )
        response = await chat_service.send_message(request, test_user.id)

        assert len(response.actions) == 1
        assert response.actions[0].action_type == "create_todo"
        assert response.actions[0].success is True

    async def test_send_message_no_model(
        self, chat_service: ChatService, test_user
    ):
        """Test sending message when model is not initialized."""
        chat_service.model = None

        request = ChatRequest(message="Hello")
        with pytest.raises(AIConfigurationError) as exc_info:
            await chat_service.send_message(request, test_user.id)
        assert "not properly initialized" in str(exc_info.value)

    async def test_send_message_timeout(
        self, chat_service: ChatService, test_user, mock_genai
    ):
        """Test message sending with timeout."""
        # Mock timeout
        chat_service.model.generate_content_async.side_effect = asyncio.TimeoutError()

        request = ChatRequest(message="Hello")
        with pytest.raises(AITimeoutError):
            await chat_service.send_message(request, test_user.id)

    async def test_send_message_ai_error(
        self, chat_service: ChatService, test_user, mock_genai
    ):
        """Test message sending with AI service error."""
        # Mock AI error
        chat_service.model.generate_content_async.side_effect = Exception("API Error")

        request = ChatRequest(message="Hello")
        with pytest.raises(AIServiceError):
            await chat_service.send_message(request, test_user.id)

    async def test_get_conversation_history(
        self, chat_service: ChatService, test_user, mock_genai
    ):
        """Test getting conversation history."""
        # First, send a message to create a conversation
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "response": "Test response",
            "actions": []
        })
        chat_service.model.generate_content_async.return_value = mock_response

        request = ChatRequest(message="Test message")
        response = await chat_service.send_message(request, test_user.id)
        conversation_id = response.conversation_id

        # Now get the history
        history = await chat_service.get_conversation_history(conversation_id, test_user.id)

        assert history.conversation_id == conversation_id
        assert len(history.messages) == 2  # User message + AI response
        assert history.messages[0].role == MessageRole.USER
        assert history.messages[1].role == MessageRole.ASSISTANT

    async def test_get_conversation_history_not_found(
        self, chat_service: ChatService, test_user
    ):
        """Test getting history for non-existent conversation."""
        fake_id = uuid.uuid4()

        with pytest.raises(AIServiceError) as exc_info:
            await chat_service.get_conversation_history(fake_id, test_user.id)
        assert "not found" in str(exc_info.value).lower()

    async def test_list_conversations(
        self, chat_service: ChatService, test_user, mock_genai
    ):
        """Test listing user conversations."""
        # Create multiple conversations
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "response": "Test",
            "actions": []
        })
        chat_service.model.generate_content_async.return_value = mock_response

        # Send messages to create conversations
        for i in range(3):
            request = ChatRequest(message=f"Message {i}")
            await chat_service.send_message(request, test_user.id)

        # List conversations
        conversations = await chat_service.list_conversations(test_user.id)

        assert len(conversations) == 3

    async def test_delete_conversation(
        self, chat_service: ChatService, test_user, mock_genai
    ):
        """Test deleting a conversation."""
        # Create a conversation
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "response": "Test",
            "actions": []
        })
        chat_service.model.generate_content_async.return_value = mock_response

        request = ChatRequest(message="Test")
        response = await chat_service.send_message(request, test_user.id)
        conversation_id = response.conversation_id

        # Delete it
        await chat_service.delete_conversation(conversation_id, test_user.id)

        # Verify it's deleted
        with pytest.raises(AIServiceError):
            await chat_service.get_conversation_history(conversation_id, test_user.id)

    async def test_delete_conversation_not_found(
        self, chat_service: ChatService, test_user
    ):
        """Test deleting non-existent conversation."""
        fake_id = uuid.uuid4()

        with pytest.raises(AIServiceError):
            await chat_service.delete_conversation(fake_id, test_user.id)

    async def test_build_system_prompt(self, chat_service: ChatService, test_user):
        """Test building system prompt."""
        prompt = await chat_service._build_system_prompt(test_user.id)

        assert "task management" in prompt.lower()
        assert "json" in prompt.lower()
        assert "actions" in prompt.lower()

    async def test_execute_actions_create_project(
        self, chat_service: ChatService, test_user
    ):
        """Test executing create_project action."""
        actions = [
            {
                "type": "create_project",
                "data": {
                    "name": "Test Project",
                    "description": "Test Description"
                }
            }
        ]

        executed_actions = await chat_service._execute_actions(actions, test_user.id)

        assert len(executed_actions) == 1
        assert executed_actions[0].action_type == "create_project"
        assert executed_actions[0].success is True
        assert executed_actions[0].data["name"] == "Test Project"

    async def test_execute_actions_create_todo(
        self, chat_service: ChatService, test_user, test_project
    ):
        """Test executing create_todo action."""
        actions = [
            {
                "type": "create_todo",
                "data": {
                    "title": "Test Todo",
                    "description": "Test Description",
                    "priority": 3,
                    "project_id": str(test_project.id)
                }
            }
        ]

        executed_actions = await chat_service._execute_actions(actions, test_user.id)

        assert len(executed_actions) == 1
        assert executed_actions[0].action_type == "create_todo"
        assert executed_actions[0].success is True

    async def test_execute_actions_invalid_type(
        self, chat_service: ChatService, test_user
    ):
        """Test executing action with invalid type."""
        actions = [
            {
                "type": "invalid_action_type",
                "data": {}
            }
        ]

        executed_actions = await chat_service._execute_actions(actions, test_user.id)

        assert len(executed_actions) == 1
        assert executed_actions[0].success is False
        assert "Unknown action type" in executed_actions[0].error

    async def test_execute_actions_error(
        self, chat_service: ChatService, test_user
    ):
        """Test executing action that fails."""
        actions = [
            {
                "type": "create_project",
                "data": {
                    # Missing required 'name' field
                    "description": "Test"
                }
            }
        ]

        executed_actions = await chat_service._execute_actions(actions, test_user.id)

        assert len(executed_actions) == 1
        assert executed_actions[0].success is False
        assert executed_actions[0].error is not None

    async def test_parse_ai_response_valid(self, chat_service: ChatService):
        """Test parsing valid AI response."""
        response_text = json.dumps({
            "response": "Here's your answer",
            "actions": [{"type": "create_project", "data": {"name": "Test"}}]
        })

        response, actions = chat_service._parse_ai_response(response_text)

        assert response == "Here's your answer"
        assert len(actions) == 1
        assert actions[0]["type"] == "create_project"

    async def test_parse_ai_response_invalid_json(self, chat_service: ChatService):
        """Test parsing invalid JSON response."""
        response_text = "This is not JSON"

        response, actions = chat_service._parse_ai_response(response_text)

        assert response == "This is not JSON"
        assert actions == []

    async def test_parse_ai_response_missing_fields(self, chat_service: ChatService):
        """Test parsing response with missing fields."""
        response_text = json.dumps({"some_field": "value"})

        response, actions = chat_service._parse_ai_response(response_text)

        assert response == response_text
        assert actions == []

    async def test_get_available_model(self, chat_service: ChatService, mock_genai):
        """Test getting available Gemini model."""
        model_name = chat_service._get_available_model()

        assert "gemini" in model_name.lower()
        assert "flash" in model_name.lower()