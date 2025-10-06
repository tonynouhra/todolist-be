# ruff: noqa: SIM117
"""
Unit tests for AIService.

This module contains comprehensive unit tests for the AIService class,
testing AI integration including subtask generation, file analysis, and error handling.
"""

import json
import uuid
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.domains.ai.service import AIService
from app.exceptions.ai import (
    AIConfigurationError,
    AIContentFilterError,
    AIInvalidRequestError,
    AIParsingError,
    AIQuotaExceededError,
    AIRateLimitError,
    AIServiceError,
    AITimeoutError,
)
from app.schemas.ai import FileAnalysisRequest, GeneratedSubtask, SubtaskGenerationRequest
from models.ai_interaction import AIInteraction


class TestAIService:
    """Test cases for AIService."""

    def test_initialize_client_success(self, test_db):
        """Test successful AI client initialization."""
        with patch("app.domains.ai.service.genai") as mock_genai:
            with patch("app.domains.ai.service.settings") as mock_settings:
                mock_settings.gemini_api_key = "test_api_key"
                mock_settings.gemini_max_tokens = 1000
                mock_settings.gemini_model = "gemini-pro"

                mock_model = MagicMock()
                mock_genai.GenerativeModel.return_value = mock_model
                mock_genai.list_models.return_value = [
                    MagicMock(
                        name="models/gemini-pro",
                        supported_generation_methods=["generateContent"],
                    )
                ]

                service = AIService(test_db)

                assert service.model is not None
                mock_genai.configure.assert_called_once_with(api_key="test_api_key")

    def test_initialize_client_no_api_key(self, test_db):
        """Test AI client initialization without API key."""
        with patch("app.domains.ai.service.settings") as mock_settings:
            mock_settings.gemini_api_key = None

            with pytest.raises(AIConfigurationError):
                AIService(test_db)

    @pytest.mark.asyncio
    async def test_generate_subtasks_success(
        self, test_db, test_user, test_todo, sample_subtask_response
    ):
        """Test successful subtask generation."""
        with patch("app.domains.ai.service.genai"):
            with patch("app.domains.ai.service.settings") as mock_settings:
                mock_settings.gemini_api_key = "test_key"
                mock_settings.ai_request_timeout = 30
                mock_settings.gemini_model = "gemini-pro"
                mock_settings.gemini_max_tokens = 1000
                mock_settings.ai_requests_per_minute = 15

                service = AIService(test_db)
                service.model = MagicMock()

                # Mock successful AI response
                mock_response = json.dumps(sample_subtask_response)
                with patch.object(service, "_generate_content_async", return_value=mock_response):
                    with patch.object(service, "_store_interaction"):
                        request = SubtaskGenerationRequest(todo_id=test_todo.id, max_subtasks=3)

                        result = await service.generate_subtasks(request, test_user.id)

                        assert result is not None
                        assert result.parent_task_title == test_todo.title
                        assert len(result.generated_subtasks) == 3
                        assert result.total_subtasks == 3

    @pytest.mark.asyncio
    async def test_generate_subtasks_nonexistent_todo(self, test_db, test_user):
        """Test subtask generation for non-existent todo."""
        with patch("app.domains.ai.service.genai"):
            with patch("app.domains.ai.service.settings") as mock_settings:
                mock_settings.gemini_api_key = "test_key"
                mock_settings.gemini_max_tokens = 1000

                service = AIService(test_db)
                service.model = MagicMock()

                fake_todo_id = uuid.uuid4()
                request = SubtaskGenerationRequest(todo_id=fake_todo_id, max_subtasks=3)

                with pytest.raises(AIInvalidRequestError):
                    await service.generate_subtasks(request, test_user.id)

    @pytest.mark.asyncio
    async def test_generate_subtasks_timeout(self, test_db, test_user, test_todo):
        """Test subtask generation timeout."""
        with patch("app.domains.ai.service.genai"):
            with patch("app.domains.ai.service.settings") as mock_settings:
                mock_settings.gemini_api_key = "test_key"
                mock_settings.ai_request_timeout = 1
                mock_settings.gemini_max_tokens = 1000

                service = AIService(test_db)
                service.model = MagicMock()

                with patch("asyncio.wait_for", side_effect=TimeoutError()):
                    request = SubtaskGenerationRequest(todo_id=test_todo.id, max_subtasks=3)

                    with pytest.raises(AITimeoutError):
                        await service.generate_subtasks(request, test_user.id)

    @pytest.mark.asyncio
    async def test_generate_subtasks_quota_exceeded(self, test_db, test_user, test_todo):
        """Test subtask generation with quota exceeded."""
        with patch("app.domains.ai.service.genai"):
            with patch("app.domains.ai.service.settings") as mock_settings:
                mock_settings.gemini_api_key = "test_key"
                mock_settings.ai_request_timeout = 30
                mock_settings.gemini_max_tokens = 1000
                mock_settings.ai_requests_per_minute = 15

                service = AIService(test_db)
                service.model = MagicMock()

                with patch.object(
                    service,
                    "_generate_content_async",
                    side_effect=Exception("quota exceeded"),
                ):
                    request = SubtaskGenerationRequest(todo_id=test_todo.id, max_subtasks=3)

                    with pytest.raises(AIQuotaExceededError):
                        await service.generate_subtasks(request, test_user.id)

    @pytest.mark.asyncio
    async def test_generate_subtasks_rate_limit(self, test_db, test_user, test_todo):
        """Test subtask generation with rate limit."""
        with patch("app.domains.ai.service.genai"):
            with patch("app.domains.ai.service.settings") as mock_settings:
                mock_settings.gemini_api_key = "test_key"
                mock_settings.ai_request_timeout = 30
                mock_settings.gemini_max_tokens = 1000
                mock_settings.ai_requests_per_minute = 15

                service = AIService(test_db)
                service.model = MagicMock()

                with patch.object(
                    service,
                    "_generate_content_async",
                    side_effect=Exception("rate limit exceeded"),
                ):
                    request = SubtaskGenerationRequest(todo_id=test_todo.id, max_subtasks=3)

                    with pytest.raises(AIRateLimitError):
                        await service.generate_subtasks(request, test_user.id)

    @pytest.mark.asyncio
    async def test_generate_subtasks_content_filter(self, test_db, test_user, test_todo):
        """Test subtask generation blocked by content filter."""
        with patch("app.domains.ai.service.genai"):
            with patch("app.domains.ai.service.settings") as mock_settings:
                mock_settings.gemini_api_key = "test_key"
                mock_settings.ai_request_timeout = 30
                mock_settings.gemini_max_tokens = 1000
                mock_settings.ai_requests_per_minute = 15

                service = AIService(test_db)
                service.model = MagicMock()

                with patch.object(
                    service,
                    "_generate_content_async",
                    side_effect=Exception("safety filters blocked"),
                ):
                    request = SubtaskGenerationRequest(todo_id=test_todo.id, max_subtasks=3)

                    with pytest.raises(AIContentFilterError):
                        await service.generate_subtasks(request, test_user.id)

    @pytest.mark.asyncio
    async def test_generate_subtasks_invalid_json(self, test_db, test_user, test_todo):
        """Test subtask generation with invalid JSON response."""
        with patch("app.domains.ai.service.genai"):
            with patch("app.domains.ai.service.settings") as mock_settings:
                mock_settings.gemini_api_key = "test_key"
                mock_settings.ai_request_timeout = 30
                mock_settings.gemini_model = "gemini-pro"
                mock_settings.gemini_max_tokens = 1000
                mock_settings.ai_requests_per_minute = 15

                service = AIService(test_db)
                service.model = MagicMock()

                with patch.object(
                    service,
                    "_generate_content_async",
                    return_value="Invalid JSON response",
                ):
                    request = SubtaskGenerationRequest(todo_id=test_todo.id, max_subtasks=3)

                    with pytest.raises(AIParsingError):
                        await service.generate_subtasks(request, test_user.id)

    @pytest.mark.asyncio
    async def test_analyze_file_success(self, test_db, test_user, sample_file_analysis_response):
        """Test successful file analysis."""
        with patch("app.domains.ai.service.genai"):
            with patch("app.domains.ai.service.settings") as mock_settings:
                mock_settings.gemini_api_key = "test_key"
                mock_settings.ai_request_timeout = 30
                mock_settings.gemini_model = "gemini-pro"
                mock_settings.gemini_max_tokens = 1000
                mock_settings.ai_requests_per_minute = 15

                service = AIService(test_db)
                service.model = MagicMock()

                # Create mock file
                mock_file = MagicMock()
                mock_file.filename = "test.txt"
                mock_file.content_type = "text/plain"
                mock_file.file_size = 1024

                mock_response = json.dumps(sample_file_analysis_response)
                with patch.object(service, "_generate_content_async", return_value=mock_response):
                    with patch.object(service, "_get_file_by_id", return_value=mock_file):
                        with patch.object(service, "_store_interaction"):
                            file_id = uuid.uuid4()
                            request = FileAnalysisRequest(file_id=file_id, analysis_type="summary")

                            result = await service.analyze_file(request, test_user.id)

                            assert result is not None
                            assert result.file_id == file_id
                            assert result.analysis_type == "summary"
                            assert result.summary == sample_file_analysis_response["summary"]

    @pytest.mark.asyncio
    async def test_analyze_file_nonexistent(self, test_db, test_user):
        """Test file analysis for non-existent file."""
        with patch("app.domains.ai.service.genai"):
            with patch("app.domains.ai.service.settings") as mock_settings:
                mock_settings.gemini_api_key = "test_key"
                mock_settings.gemini_max_tokens = 1000

                service = AIService(test_db)
                service.model = MagicMock()

                with patch.object(service, "_get_file_by_id", return_value=None):
                    file_id = uuid.uuid4()
                    request = FileAnalysisRequest(file_id=file_id, analysis_type="summary")

                    with pytest.raises(AIInvalidRequestError):
                        await service.analyze_file(request, test_user.id)

    @pytest.mark.asyncio
    async def test_get_service_status_healthy(self, test_db):
        """Test getting healthy service status."""
        with patch("app.domains.ai.service.genai"):
            with patch("app.domains.ai.service.settings") as mock_settings:
                mock_settings.gemini_api_key = "test_key"
                mock_settings.gemini_model = "gemini-pro"
                mock_settings.gemini_max_tokens = 1000
                mock_settings.ai_requests_per_minute = 15

                service = AIService(test_db)
                service.model = MagicMock()

                with patch.object(service, "_generate_content_async", return_value="OK"):
                    status = await service.get_service_status()

                    assert status.service_available is True
                    assert status.model_name == "gemini-pro"
                    assert status.requests_today >= 0

    @pytest.mark.asyncio
    async def test_get_service_status_no_api_key(self, test_db):
        """Test service status without API key."""
        with patch("app.domains.ai.service.settings") as mock_settings:
            mock_settings.gemini_api_key = None
            mock_settings.gemini_model = "gemini-pro"

            # This will fail during initialization
            with pytest.raises(AIConfigurationError):
                AIService(test_db)

    @pytest.mark.asyncio
    async def test_get_service_status_timeout(self, test_db):
        """Test service status check timeout."""
        with patch("app.domains.ai.service.genai"):
            with patch("app.domains.ai.service.settings") as mock_settings:
                mock_settings.gemini_api_key = "test_key"
                mock_settings.gemini_model = "gemini-pro"
                mock_settings.gemini_max_tokens = 1000

                service = AIService(test_db)
                service.model = MagicMock()

                with patch("asyncio.wait_for", side_effect=TimeoutError()):
                    status = await service.get_service_status()

                    assert status.service_available is False

    def test_build_subtask_generation_prompt(self, test_db, test_todo):
        """Test building subtask generation prompt."""
        with patch("app.domains.ai.service.genai"):
            with patch("app.domains.ai.service.settings") as mock_settings:
                mock_settings.gemini_api_key = "test_key"
                mock_settings.gemini_max_tokens = 1000

                service = AIService(test_db)

                prompt = service._build_subtask_generation_prompt_from_todo(test_todo, 3, 5)

                assert test_todo.title in prompt
                assert "5" in prompt  # max_subtasks
                assert "JSON" in prompt
                assert "subtasks" in prompt

    def test_build_file_analysis_prompt(self, test_db):
        """Test building file analysis prompt."""
        with patch("app.domains.ai.service.genai"):
            with patch("app.domains.ai.service.settings") as mock_settings:
                mock_settings.gemini_api_key = "test_key"
                mock_settings.gemini_max_tokens = 1000

                service = AIService(test_db)

                mock_file = MagicMock()
                mock_file.filename = "test.txt"
                mock_file.content_type = "text/plain"
                mock_file.file_size = 1024

                prompt = service._build_file_analysis_prompt(
                    mock_file, "summary", "Additional context"
                )

                assert "test.txt" in prompt
                assert "summary" in prompt
                assert "Additional context" in prompt
                assert "JSON" in prompt

    @pytest.mark.asyncio
    async def test_generate_content_async_success(self, test_db):
        """Test successful async content generation."""
        with patch("app.domains.ai.service.genai"):
            with patch("app.domains.ai.service.settings") as mock_settings:
                mock_settings.gemini_api_key = "test_key"
                mock_settings.gemini_max_tokens = 1000

                service = AIService(test_db)
                mock_model = MagicMock()
                mock_response = MagicMock()
                mock_response.text = "Generated response"
                mock_model.generate_content.return_value = mock_response
                service.model = mock_model

                result = await service._generate_content_async("Test prompt")

                assert result == "Generated response"
                mock_model.generate_content.assert_called_once_with("Test prompt")

    @pytest.mark.asyncio
    async def test_generate_content_async_empty_response(self, test_db):
        """Test async content generation with empty response."""
        with patch("app.domains.ai.service.genai"):
            with patch("app.domains.ai.service.settings") as mock_settings:
                mock_settings.gemini_api_key = "test_key"
                mock_settings.gemini_max_tokens = 1000

                service = AIService(test_db)
                mock_model = MagicMock()
                mock_response = MagicMock()
                mock_response.text = None
                mock_model.generate_content.return_value = mock_response
                service.model = mock_model

                with pytest.raises(AIServiceError):
                    await service._generate_content_async("Test prompt")

    def test_parse_subtask_response_success(self, test_db, sample_subtask_response):
        """Test successful subtask response parsing."""
        with patch("app.domains.ai.service.genai"):
            with patch("app.domains.ai.service.settings") as mock_settings:
                mock_settings.gemini_api_key = "test_key"
                mock_settings.gemini_max_tokens = 1000

                service = AIService(test_db)

                response_text = f"```json\n{json.dumps(sample_subtask_response)}\n```"
                result = service._parse_subtask_response(response_text)

                assert len(result) == 3
                assert all(isinstance(subtask, GeneratedSubtask) for subtask in result)
                assert result[0].title == "Research the topic"

    def test_parse_subtask_response_no_json(self, test_db):
        """Test subtask response parsing with no JSON."""
        with patch("app.domains.ai.service.genai"):
            with patch("app.domains.ai.service.settings") as mock_settings:
                mock_settings.gemini_api_key = "test_key"
                mock_settings.gemini_max_tokens = 1000

                service = AIService(test_db)

                with pytest.raises(AIParsingError):
                    service._parse_subtask_response("No JSON here")

    def test_parse_subtask_response_invalid_json(self, test_db):
        """Test subtask response parsing with invalid JSON."""
        with patch("app.domains.ai.service.genai"):
            with patch("app.domains.ai.service.settings") as mock_settings:
                mock_settings.gemini_api_key = "test_key"
                mock_settings.gemini_max_tokens = 1000

                service = AIService(test_db)

                with pytest.raises(AIParsingError):
                    service._parse_subtask_response('{"invalid": json}')

    def test_parse_file_analysis_response_success(self, test_db, sample_file_analysis_response):
        """Test successful file analysis response parsing."""
        with patch("app.domains.ai.service.genai"):
            with patch("app.domains.ai.service.settings") as mock_settings:
                mock_settings.gemini_api_key = "test_key"
                mock_settings.gemini_max_tokens = 1000

                service = AIService(test_db)

                response_text = f"```json\n{json.dumps(sample_file_analysis_response)}\n```"
                result = service._parse_file_analysis_response(response_text)

                assert result == sample_file_analysis_response
                assert "summary" in result
                assert "key_points" in result

    @pytest.mark.asyncio
    async def test_store_interaction_success(self, test_db, test_user, test_todo):
        """Test successful AI interaction storage."""
        with patch("app.domains.ai.service.genai"):
            with patch("app.domains.ai.service.settings") as mock_settings:
                mock_settings.gemini_api_key = "test_key"
                mock_settings.gemini_max_tokens = 1000

                service = AIService(test_db)

                await service._store_interaction(
                    user_id=test_user.id,
                    todo_id=test_todo.id,
                    prompt="Test prompt",
                    response="Test response",
                    interaction_type="subtask_generation",
                )

                # Verify interaction was stored
                from sqlalchemy import select

                result = await test_db.execute(
                    select(AIInteraction).where(AIInteraction.user_id == test_user.id)
                )
                interaction = result.scalar_one_or_none()

                assert interaction is not None
                assert interaction.prompt == "Test prompt"
                assert interaction.response == "Test response"
                assert interaction.interaction_type == "subtask_generation"

    @pytest.mark.asyncio
    async def test_store_interaction_database_error(self, test_db, test_user):
        """Test AI interaction storage with database error."""
        with patch("app.domains.ai.service.genai"):
            with patch("app.domains.ai.service.settings") as mock_settings:
                mock_settings.gemini_api_key = "test_key"
                mock_settings.gemini_max_tokens = 1000

                service = AIService(test_db)

                with patch.object(test_db, "commit", side_effect=SQLAlchemyError("DB Error")):
                    with patch.object(test_db, "rollback") as mock_rollback:
                        # Should not raise exception (graceful failure)
                        await service._store_interaction(
                            user_id=test_user.id,
                            prompt="Test prompt",
                            response="Test response",
                            interaction_type="test",
                        )
                        mock_rollback.assert_called_once()

    def test_get_available_model_configured_model(self, test_db):
        """Test getting available model when configured model exists."""
        with patch("app.domains.ai.service.genai") as mock_genai:
            with patch("app.domains.ai.service.settings") as mock_settings:
                mock_settings.gemini_api_key = "test_key"
                mock_settings.gemini_model = "gemini-pro"
                mock_settings.gemini_max_tokens = 1000

                mock_model_1 = MagicMock()
                mock_model_1.name = "models/gemini-pro"
                mock_model_1.supported_generation_methods = ["generateContent"]

                mock_model_2 = MagicMock()
                mock_model_2.name = "models/gemini-1.5-flash"
                mock_model_2.supported_generation_methods = ["generateContent"]

                mock_genai.list_models.return_value = [mock_model_1, mock_model_2]

                service = AIService(test_db)
                result = service._get_available_model()

                assert "gemini-pro" in result

    def test_get_available_model_fallback(self, test_db):
        """Test getting available model with fallback."""
        with patch("app.domains.ai.service.genai") as mock_genai:
            with patch("app.domains.ai.service.settings") as mock_settings:
                mock_settings.gemini_api_key = "test_key"
                mock_settings.gemini_model = "nonexistent-model"
                mock_settings.gemini_max_tokens = 1000

                mock_model = MagicMock()
                mock_model.name = "models/gemini-1.5-flash"
                mock_model.supported_generation_methods = ["generateContent"]

                mock_genai.list_models.return_value = [mock_model]

                service = AIService(test_db)
                result = service._get_available_model()

                assert "gemini-1.5-flash" in result
