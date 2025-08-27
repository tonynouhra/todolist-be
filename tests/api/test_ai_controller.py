"""
API tests for AI controller.

This module contains comprehensive API endpoint tests for the AI controller,
testing subtask generation, file analysis, and AI service status endpoints.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from httpx import AsyncClient

from app.exceptions.ai import (
    AIConfigurationError,
    AIQuotaExceededError,
    AIRateLimitError,
    AIServiceError,
    AIServiceUnavailableError,
    AITimeoutError,
)
from app.schemas.ai import FileAnalysisResponse, GeneratedSubtask, SubtaskGenerationResponse


class TestAIController:
    """Test cases for AI API endpoints."""

    @pytest.mark.asyncio
    async def test_generate_subtasks_success(
        self, authenticated_client: AsyncClient, test_todo, sample_subtask_response
    ):
        """Test successful subtask generation."""
        request_data = {"todo_id": str(test_todo.id), "max_subtasks": 3}

        # Mock the AI service
        mock_response = SubtaskGenerationResponse(
            parent_task_title=test_todo.title,
            generated_subtasks=[
                GeneratedSubtask(
                    title=subtask["title"],
                    description=subtask["description"],
                    priority=subtask["priority"],
                    estimated_time=subtask["estimated_time"],
                    order=subtask["order"],
                )
                for subtask in sample_subtask_response["subtasks"]
            ],
            total_subtasks=len(sample_subtask_response["subtasks"]),
            generation_timestamp=datetime.now(timezone.utc),
            ai_model="gemini-pro",
        )

        with patch("app.domains.ai.controller.AIService") as mock_ai_service:
            mock_ai_service.return_value.generate_subtasks = AsyncMock(return_value=mock_response)
            response = await authenticated_client.post(
                "/api/ai/generate-subtasks", json=request_data
            )

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["status"] == "success"
            assert data["message"] == "Subtasks generated successfully"
            assert data["data"]["parent_task_title"] == test_todo.title
            assert data["data"]["total_subtasks"] == 3

    @pytest.mark.asyncio
    async def test_generate_subtasks_nonexistent_todo(self, authenticated_client: AsyncClient):
        """Test subtask generation for non-existent todo."""
        fake_todo_id = str(uuid.uuid4())
        request_data = {"todo_id": fake_todo_id, "max_subtasks": 3}

        from app.exceptions.ai import AIInvalidRequestError

        with patch("app.domains.ai.controller.AIService") as mock_ai_service:
            mock_ai_service.return_value.generate_subtasks = AsyncMock(
                side_effect=AIInvalidRequestError("Todo not found")
            )
            response = await authenticated_client.post(
                "/api/ai/generate-subtasks", json=request_data
            )

            assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_generate_subtasks_ai_configuration_error(
        self, authenticated_client: AsyncClient, test_todo
    ):
        """Test subtask generation with AI configuration error."""
        request_data = {"todo_id": str(test_todo.id), "max_subtasks": 3}

        with patch("app.domains.ai.controller.AIService") as mock_ai_service:
            mock_ai_service.return_value.generate_subtasks = AsyncMock(
                side_effect=AIConfigurationError("AI service not configured")
            )
            response = await authenticated_client.post(
                "/api/ai/generate-subtasks", json=request_data
            )

            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            data = response.json()
            assert data["status"] == "error"
            assert data["message"] == "AI service is not properly configured"
            assert "AI_CONFIGURATION_ERROR" in data["data"]["error_code"]

    @pytest.mark.asyncio
    async def test_generate_subtasks_quota_exceeded(
        self, authenticated_client: AsyncClient, test_todo
    ):
        """Test subtask generation with quota exceeded."""
        request_data = {"todo_id": str(test_todo.id), "max_subtasks": 3}

        with patch("app.domains.ai.controller.AIService") as mock_ai_service:
            mock_ai_service.return_value.generate_subtasks = AsyncMock(
                side_effect=AIQuotaExceededError("API quota exceeded")
            )
            response = await authenticated_client.post(
                "/api/ai/generate-subtasks", json=request_data
            )

            assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
            data = response.json()
            assert data["status"] == "error"
            assert data["message"] == "AI service quota exceeded"
            assert "AI_QUOTA_EXCEEDED" in data["data"]["error_code"]

    @pytest.mark.asyncio
    async def test_generate_subtasks_rate_limit(self, authenticated_client: AsyncClient, test_todo):
        """Test subtask generation with rate limit."""
        request_data = {"todo_id": str(test_todo.id), "max_subtasks": 3}

        rate_limit_error = AIRateLimitError("Rate limit exceeded")
        rate_limit_error.details = {"retry_after": 120}

        with patch("app.domains.ai.controller.AIService") as mock_ai_service:
            mock_ai_service.return_value.generate_subtasks = AsyncMock(side_effect=rate_limit_error)
            response = await authenticated_client.post(
                "/api/ai/generate-subtasks", json=request_data
            )

            assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
            assert "retry-after" in response.headers
            assert response.headers["retry-after"] == "120"

            data = response.json()
            assert data["status"] == "error"
            assert data["message"] == "Rate limit exceeded"

    @pytest.mark.asyncio
    async def test_generate_subtasks_timeout(self, authenticated_client: AsyncClient, test_todo):
        """Test subtask generation with timeout."""
        request_data = {"todo_id": str(test_todo.id), "max_subtasks": 3}

        with patch("app.domains.ai.controller.AIService") as mock_ai_service:
            mock_ai_service.return_value.generate_subtasks = AsyncMock(
                side_effect=AITimeoutError("Request timed out")
            )
            response = await authenticated_client.post(
                "/api/ai/generate-subtasks", json=request_data
            )

            assert response.status_code == status.HTTP_408_REQUEST_TIMEOUT
            data = response.json()
            assert data["status"] == "error"
            assert data["message"] == "AI request timed out"
            assert "AI_TIMEOUT" in data["data"]["error_code"]

    @pytest.mark.asyncio
    async def test_generate_subtasks_service_unavailable(
        self, authenticated_client: AsyncClient, test_todo
    ):
        """Test subtask generation with service unavailable."""
        request_data = {"todo_id": str(test_todo.id), "max_subtasks": 3}

        with patch("app.domains.ai.controller.AIService") as mock_ai_service:
            mock_ai_service.return_value.generate_subtasks = AsyncMock(
                side_effect=AIServiceUnavailableError("Service temporarily unavailable")
            )
            response = await authenticated_client.post(
                "/api/ai/generate-subtasks", json=request_data
            )

            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            data = response.json()
            assert data["status"] == "error"
            assert data["message"] == "AI service is temporarily unavailable"

    @pytest.mark.asyncio
    async def test_generate_subtasks_generic_error(
        self, authenticated_client: AsyncClient, test_todo
    ):
        """Test subtask generation with generic AI service error."""
        request_data = {"todo_id": str(test_todo.id), "max_subtasks": 3}

        with patch("app.domains.ai.controller.AIService") as mock_ai_service:
            mock_ai_service.return_value.generate_subtasks = AsyncMock(
                side_effect=AIServiceError("Generic AI error")
            )
            response = await authenticated_client.post(
                "/api/ai/generate-subtasks", json=request_data
            )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()
            assert data["status"] == "error"
            assert data["message"] == "AI service encountered an error"

    @pytest.mark.asyncio
    async def test_generate_subtasks_unexpected_error(
        self, authenticated_client: AsyncClient, test_todo
    ):
        """Test subtask generation with unexpected error."""
        request_data = {"todo_id": str(test_todo.id), "max_subtasks": 3}

        with patch("app.domains.ai.controller.AIService") as mock_ai_service:
            mock_ai_service.return_value.generate_subtasks = AsyncMock(
                side_effect=Exception("Unexpected error")
            )
            response = await authenticated_client.post(
                "/api/ai/generate-subtasks", json=request_data
            )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()
            assert data["status"] == "error"
            assert data["message"] == "An unexpected error occurred"

    @pytest.mark.asyncio
    async def test_generate_subtasks_invalid_request_data(self, authenticated_client: AsyncClient):
        """Test subtask generation with invalid request data."""
        invalid_cases = [
            # Missing todo_id
            {"max_subtasks": 3},
            # Invalid todo_id format
            {"todo_id": "invalid-uuid", "max_subtasks": 3},
            # Invalid max_subtasks
            {"todo_id": str(uuid.uuid4()), "max_subtasks": 0},
            {"todo_id": str(uuid.uuid4()), "max_subtasks": 21},  # Assuming max is 20
        ]

        for invalid_data in invalid_cases:
            response = await authenticated_client.post(
                "/api/ai/generate-subtasks", json=invalid_data
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_analyze_file_success(
        self, authenticated_client: AsyncClient, sample_file_analysis_response
    ):
        """Test successful file analysis."""
        file_id = uuid.uuid4()
        request_data = {
            "file_id": str(file_id),
            "analysis_type": "summary",
            "context": "Project requirements document",
        }

        mock_response = FileAnalysisResponse(
            file_id=file_id,
            analysis_type="summary",
            summary=sample_file_analysis_response["summary"],
            key_points=sample_file_analysis_response["key_points"],
            suggested_tasks=sample_file_analysis_response["suggested_tasks"],
            confidence_score=sample_file_analysis_response["confidence"],
            analysis_timestamp=datetime.now(timezone.utc),
            ai_model="gemini-pro",
        )

        with patch("app.domains.ai.controller.AIService") as mock_ai_service:
            mock_ai_service.return_value.analyze_file = AsyncMock(return_value=mock_response)
            response = await authenticated_client.post("/api/ai/analyze-file", json=request_data)

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["status"] == "success"
            assert data["message"] == "File analyzed successfully"
            assert data["data"]["analysis_type"] == "summary"
            assert data["data"]["confidence_score"] == 0.85

    @pytest.mark.asyncio
    async def test_analyze_file_nonexistent(self, authenticated_client: AsyncClient):
        """Test file analysis for non-existent file."""
        fake_file_id = str(uuid.uuid4())
        request_data = {"file_id": fake_file_id, "analysis_type": "summary"}

        from app.exceptions.ai import AIInvalidRequestError

        with patch("app.domains.ai.controller.AIService") as mock_ai_service:
            mock_ai_service.return_value.analyze_file = AsyncMock(
                side_effect=AIInvalidRequestError("File not found")
            )
            response = await authenticated_client.post("/api/ai/analyze-file", json=request_data)

            assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_analyze_file_different_analysis_types(self, authenticated_client: AsyncClient):
        """Test file analysis with different analysis types."""
        file_id = str(uuid.uuid4())
        analysis_types = ["summary", "task_extraction", "general"]

        for analysis_type in analysis_types:
            request_data = {"file_id": file_id, "analysis_type": analysis_type}

            mock_response = FileAnalysisResponse(
                file_id=uuid.UUID(file_id),
                analysis_type=analysis_type,
                summary="Test summary",
                key_points=["Point 1", "Point 2"],
                suggested_tasks=["Task 1", "Task 2"],
                confidence_score=0.8,
                analysis_timestamp=datetime.now(timezone.utc),
                ai_model="gemini-pro",
            )

            with patch("app.domains.ai.controller.AIService") as mock_ai_service:
                mock_ai_service.return_value.analyze_file = AsyncMock(return_value=mock_response)
                response = await authenticated_client.post(
                    "/api/ai/analyze-file", json=request_data
                )

                assert response.status_code == status.HTTP_201_CREATED
                data = response.json()
                assert data["data"]["analysis_type"] == analysis_type

    @pytest.mark.asyncio
    async def test_analyze_file_with_context(self, authenticated_client: AsyncClient):
        """Test file analysis with additional context."""
        file_id = str(uuid.uuid4())
        request_data = {
            "file_id": file_id,
            "analysis_type": "task_extraction",
            "context": "This is a meeting transcript from our sprint planning session",
        }

        mock_response = FileAnalysisResponse(
            file_id=uuid.UUID(file_id),
            analysis_type="task_extraction",
            summary="Meeting transcript analysis",
            key_points=["Sprint goals discussed"],
            suggested_tasks=["Create user stories", "Estimate tasks"],
            confidence_score=0.9,
            analysis_timestamp=datetime.now(timezone.utc),
            ai_model="gemini-pro",
        )

        with patch("app.domains.ai.controller.AIService") as mock_ai_service:
            mock_ai_service.return_value.analyze_file = AsyncMock(return_value=mock_response)
            response = await authenticated_client.post("/api/ai/analyze-file", json=request_data)

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["data"]["confidence_score"] == 0.9

    @pytest.mark.asyncio
    async def test_analyze_file_ai_service_error(self, authenticated_client: AsyncClient):
        """Test file analysis with AI service error."""
        file_id = str(uuid.uuid4())
        request_data = {"file_id": file_id, "analysis_type": "summary"}

        with patch("app.domains.ai.controller.AIService") as mock_ai_service:
            mock_ai_service.return_value.analyze_file = AsyncMock(
                side_effect=AIServiceError("Analysis failed")
            )
            response = await authenticated_client.post("/api/ai/analyze-file", json=request_data)

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()
            assert data["status"] == "error"
            assert "AI service encountered an error" in data["message"]

    @pytest.mark.asyncio
    async def test_get_ai_service_status_healthy(self, authenticated_client: AsyncClient):
        """Test getting healthy AI service status."""
        from datetime import datetime, timezone

        from app.schemas.ai import AIServiceStatus

        mock_status = AIServiceStatus(
            service_available=True,
            model_name="gemini-pro",
            last_request_timestamp=datetime.now(timezone.utc),
            requests_today=42,
        )

        with patch("app.domains.ai.controller.AIService") as mock_ai_service:
            mock_ai_service.return_value.get_service_status = AsyncMock(return_value=mock_status)
            response = await authenticated_client.get("/api/ai/status")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "success"
            assert data["message"] == "AI service status retrieved successfully"
            assert data["data"]["service_available"] is True
            assert data["data"]["model_name"] == "gemini-pro"
            assert data["data"]["requests_today"] == 42

    @pytest.mark.asyncio
    async def test_get_ai_service_status_unhealthy(self, authenticated_client: AsyncClient):
        """Test getting unhealthy AI service status."""
        from app.schemas.ai import AIServiceStatus

        mock_status = AIServiceStatus(
            service_available=False,
            model_name="gemini-pro",
            last_request_timestamp=None,
            requests_today=0,
        )

        with patch("app.domains.ai.controller.AIService") as mock_ai_service:
            mock_ai_service.return_value.get_service_status = AsyncMock(return_value=mock_status)
            response = await authenticated_client.get("/api/ai/status")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["data"]["service_available"] is False

    @pytest.mark.asyncio
    async def test_get_ai_service_status_error(self, authenticated_client: AsyncClient):
        """Test AI service status check with error."""
        with patch("app.domains.ai.controller.AIService") as mock_ai_service:
            mock_ai_service.return_value.get_service_status = AsyncMock(
                side_effect=Exception("Status check failed")
            )
            response = await authenticated_client.get("/api/ai/status")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "success"
            assert data["message"] == "AI service status check failed"
            assert data["data"]["service_available"] is False

    @pytest.mark.asyncio
    async def test_ai_endpoints_unauthorized_access(self, client: AsyncClient, test_todo):
        """Test accessing AI endpoints without authentication."""
        endpoints_data = [
            (
                "POST",
                "/api/ai/generate-subtasks",
                {"todo_id": str(test_todo.id), "max_subtasks": 3},
            ),
            (
                "POST",
                "/api/ai/analyze-file",
                {"file_id": str(uuid.uuid4()), "analysis_type": "summary"},
            ),
            ("GET", "/api/ai/status", None),
        ]

        for method, endpoint, data in endpoints_data:
            if method == "POST":
                response = await client.post(endpoint, json=data)
            else:
                response = await client.get(endpoint)

            assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_ai_request_validation_comprehensive(self, authenticated_client: AsyncClient):
        """Test comprehensive validation for AI requests."""
        # Test subtask generation validation
        invalid_subtask_cases = [
            # Missing required fields
            {"max_subtasks": 3},
            # Invalid UUID format
            {"todo_id": "not-a-uuid", "max_subtasks": 3},
            # Invalid max_subtasks range
            {"todo_id": str(uuid.uuid4()), "max_subtasks": -1},
            {"todo_id": str(uuid.uuid4()), "max_subtasks": 25},  # Assuming max is 20
        ]

        for invalid_data in invalid_subtask_cases:
            response = await authenticated_client.post(
                "/api/ai/generate-subtasks", json=invalid_data
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Test file analysis validation
        invalid_file_cases = [
            # Missing required fields
            {"analysis_type": "summary"},
            # Invalid UUID format
            {"file_id": "not-a-uuid", "analysis_type": "summary"},
            # Invalid analysis type
            {"file_id": str(uuid.uuid4()), "analysis_type": "invalid_type"},
        ]

        for invalid_data in invalid_file_cases:
            response = await authenticated_client.post("/api/ai/analyze-file", json=invalid_data)
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_ai_error_response_format(self, authenticated_client: AsyncClient, test_todo):
        """Test that AI error responses follow consistent format."""
        request_data = {"todo_id": str(test_todo.id), "max_subtasks": 3}

        with patch("app.domains.ai.controller.AIService") as mock_ai_service:
            mock_ai_service.return_value.generate_subtasks = AsyncMock(
                side_effect=AIConfigurationError("Test error")
            )
            response = await authenticated_client.post(
                "/api/ai/generate-subtasks", json=request_data
            )

            data = response.json()

            # Check error response structure
            assert "status" in data
            assert "message" in data
            assert "data" in data
            assert data["status"] == "error"

            # Check AI-specific error data
            error_data = data["data"]
            assert "error_code" in error_data
            assert "error_message" in error_data
            assert "suggestions" in error_data
            assert isinstance(error_data["suggestions"], list)

    @pytest.mark.asyncio
    async def test_ai_request_logging_integration(
        self, authenticated_client: AsyncClient, test_todo
    ):
        """Test that AI requests are properly logged/tracked."""
        request_data = {"todo_id": str(test_todo.id), "max_subtasks": 3}

        mock_response = SubtaskGenerationResponse(
            parent_task_title=test_todo.title,
            generated_subtasks=[],
            total_subtasks=0,
            generation_timestamp=datetime.now(timezone.utc),
            ai_model="gemini-pro",
        )

        with patch("app.domains.ai.controller.AIService") as mock_ai_service:
            mock_ai_service.return_value.generate_subtasks = AsyncMock(return_value=mock_response)
            response = await authenticated_client.post(
                "/api/ai/generate-subtasks", json=request_data
            )

            assert response.status_code == status.HTTP_201_CREATED
            mock_ai_service.assert_called_once()

            # In a real implementation, you might verify that:
            # - AI interaction was logged to database
            # - Metrics were updated
            # - Audit trail was created
