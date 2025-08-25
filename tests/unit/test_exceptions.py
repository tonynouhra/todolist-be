"""
Unit tests for Exception classes.

This module contains comprehensive unit tests for custom exception classes
used throughout the application.
"""

import pytest
from fastapi import HTTPException, status

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
from app.exceptions.base import BaseAppException, NotFoundError
from app.exceptions.todo import (
    InvalidTodoOperationError,
    MaxTodoDepthExceededError,
    TodoNotFoundError,
    TodoPermissionError,
)
from app.exceptions.user import (
    UserAlreadyExistsError,
    UserNotFoundError,
    UserPermissionError,
)


class TestBaseAppException:
    """Test cases for BaseAppException."""

    def test_base_exception_default_values(self):
        """Test BaseAppException with default values."""
        exc = BaseAppException("Test error")
        
        assert exc.message == "Test error"
        assert exc.status_code == 500
        assert exc.error_code == "INTERNAL_ERROR"
        assert exc.details == {}
        assert exc.detail["message"] == "Test error"
        assert exc.detail["error_code"] == "INTERNAL_ERROR"
        assert exc.detail["details"] == {}

    def test_base_exception_custom_values(self):
        """Test BaseAppException with custom values."""
        details = {"field": "value", "context": "test"}
        exc = BaseAppException(
            message="Custom error",
            status_code=400,
            error_code="CUSTOM_ERROR",
            details=details
        )
        
        assert exc.message == "Custom error"
        assert exc.status_code == 400
        assert exc.error_code == "CUSTOM_ERROR"
        assert exc.details == details
        assert exc.detail["message"] == "Custom error"
        assert exc.detail["error_code"] == "CUSTOM_ERROR"
        assert exc.detail["details"] == details

    def test_base_exception_inheritance(self):
        """Test that BaseAppException inherits from HTTPException."""
        exc = BaseAppException("Test error")
        assert isinstance(exc, HTTPException)

    def test_base_exception_none_details(self):
        """Test BaseAppException with None details."""
        exc = BaseAppException("Test error", details=None)
        assert exc.details == {}


class TestNotFoundError:
    """Test cases for NotFoundError."""

    def test_not_found_error_default(self):
        """Test NotFoundError with default behavior."""
        exc = NotFoundError("Resource not found")
        
        assert exc.message == "Resource not found"
        assert exc.status_code == 404
        assert exc.error_code == "NOT_FOUND"


class TestTodoExceptions:
    """Test cases for Todo-related exceptions."""

    def test_todo_not_found_error(self):
        """Test TodoNotFoundError."""
        exc = TodoNotFoundError("Todo with ID 123 not found")
        
        assert exc.message == "Todo with ID 123 not found"
        assert exc.status_code == 404
        assert exc.error_code == "TODO_NOT_FOUND"
        assert isinstance(exc, BaseAppException)

    def test_todo_permission_error(self):
        """Test TodoPermissionError."""
        exc = TodoPermissionError("Access denied to todo")
        
        assert exc.message == "Access denied to todo"
        assert exc.status_code == 403
        assert exc.error_code == "TODO_PERMISSION_DENIED"

    def test_invalid_todo_operation_error(self):
        """Test InvalidTodoOperationError."""
        exc = InvalidTodoOperationError("Cannot delete completed todo")
        
        assert exc.message == "Cannot delete completed todo"
        assert exc.status_code == 400
        assert exc.error_code == "INVALID_TODO_OPERATION"

    def test_max_todo_depth_exceeded_error(self):
        """Test MaxTodoDepthExceededError."""
        exc = MaxTodoDepthExceededError("Maximum nesting depth of 5 exceeded")
        
        assert exc.message == "Maximum nesting depth of 5 exceeded"
        assert exc.status_code == 400
        assert exc.error_code == "MAX_TODO_DEPTH_EXCEEDED"


class TestUserExceptions:
    """Test cases for User-related exceptions."""

    def test_user_not_found_error(self):
        """Test UserNotFoundError."""
        exc = UserNotFoundError("User with ID user_123 not found")
        
        assert exc.message == "User with ID user_123 not found"
        assert exc.status_code == 404
        assert exc.error_code == "USER_NOT_FOUND"

    def test_user_already_exists_error(self):
        """Test UserAlreadyExistsError."""
        exc = UserAlreadyExistsError("User with email test@example.com already exists")
        
        assert exc.message == "User with email test@example.com already exists"
        assert exc.status_code == 409
        assert exc.error_code == "USER_ALREADY_EXISTS"

    def test_user_permission_error(self):
        """Test UserPermissionError."""
        exc = UserPermissionError("Access denied to user profile")
        
        assert exc.message == "Access denied to user profile"
        assert exc.status_code == 403
        assert exc.error_code == "USER_PERMISSION_DENIED"


class TestAIExceptions:
    """Test cases for AI-related exceptions."""

    def test_ai_service_error(self):
        """Test base AIServiceError."""
        exc = AIServiceError("AI service encountered an error")
        
        assert exc.message == "AI service encountered an error"
        assert exc.status_code == 500
        assert exc.error_code == "AI_SERVICE_ERROR"

    def test_ai_configuration_error(self):
        """Test AIConfigurationError."""
        exc = AIConfigurationError("AI service not configured properly")
        
        assert exc.message == "AI service not configured properly"
        assert exc.status_code == 503
        assert exc.error_code == "AI_CONFIGURATION_ERROR"

    def test_ai_quota_exceeded_error(self):
        """Test AIQuotaExceededError."""
        exc = AIQuotaExceededError("API quota exceeded for this month")
        
        assert exc.message == "API quota exceeded for this month"
        assert exc.status_code == 429
        assert exc.error_code == "AI_QUOTA_EXCEEDED"

    def test_ai_rate_limit_error(self):
        """Test AIRateLimitError."""
        exc = AIRateLimitError("Rate limit exceeded, try again later")
        
        assert exc.message == "Rate limit exceeded, try again later"
        assert exc.status_code == 429
        assert exc.error_code == "AI_RATE_LIMITED"

    def test_ai_rate_limit_error_with_details(self):
        """Test AIRateLimitError with retry details."""
        details = {"retry_after": 60, "limit": 100}
        exc = AIRateLimitError("Rate limit exceeded", details=details)
        
        assert exc.details == details
        assert exc.details["retry_after"] == 60

    def test_ai_timeout_error(self):
        """Test AITimeoutError."""
        exc = AITimeoutError("Request timed out after 30 seconds")
        
        assert exc.message == "Request timed out after 30 seconds"
        assert exc.status_code == 408
        assert exc.error_code == "AI_TIMEOUT"

    def test_ai_service_unavailable_error(self):
        """Test AIServiceUnavailableError."""
        exc = AIServiceUnavailableError("AI service is temporarily unavailable")
        
        assert exc.message == "AI service is temporarily unavailable"
        assert exc.status_code == 503
        assert exc.error_code == "AI_SERVICE_UNAVAILABLE"

    def test_ai_invalid_request_error(self):
        """Test AIInvalidRequestError."""
        exc = AIInvalidRequestError("Invalid request format")
        
        assert exc.message == "Invalid request format"
        assert exc.status_code == 400
        assert exc.error_code == "AI_INVALID_REQUEST"

    def test_ai_parsing_error(self):
        """Test AIParsingError."""
        exc = AIParsingError("Failed to parse AI response")
        
        assert exc.message == "Failed to parse AI response"
        assert exc.status_code == 502
        assert exc.error_code == "AI_PARSING_ERROR"

    def test_ai_content_filter_error(self):
        """Test AIContentFilterError."""
        exc = AIContentFilterError("Content was blocked by AI safety filters")
        
        assert exc.message == "Content was blocked by AI safety filters"
        assert exc.status_code == 400
        assert exc.error_code == "AI_CONTENT_FILTERED"


class TestExceptionChaining:
    """Test exception chaining and context."""

    def test_exception_chaining(self):
        """Test that exceptions can be chained properly."""
        try:
            # Simulate nested exception
            try:
                raise ValueError("Original error")
            except ValueError as e:
                raise TodoNotFoundError("Todo not found") from e
        except TodoNotFoundError as todo_exc:
            assert todo_exc.message == "Todo not found"
            assert isinstance(todo_exc.__cause__, ValueError)
            assert str(todo_exc.__cause__) == "Original error"

    def test_exception_with_complex_details(self):
        """Test exceptions with complex detail objects."""
        details = {
            "validation_errors": [
                {"field": "title", "error": "Required"},
                {"field": "priority", "error": "Must be between 1 and 5"}
            ],
            "request_id": "req_123",
            "timestamp": "2023-01-01T00:00:00Z",
            "user_id": "user_456"
        }
        
        exc = InvalidTodoOperationError("Validation failed", details=details)
        
        assert exc.details["validation_errors"] == details["validation_errors"]
        assert exc.details["request_id"] == "req_123"
        assert exc.details["user_id"] == "user_456"

    def test_exception_status_code_inheritance(self):
        """Test that status codes are properly inherited."""
        # All not found errors should have 404
        todo_not_found = TodoNotFoundError("Todo not found")
        user_not_found = UserNotFoundError("User not found")
        
        assert todo_not_found.status_code == 404
        assert user_not_found.status_code == 404
        
        # All permission errors should have 403
        todo_permission = TodoPermissionError("Access denied")
        user_permission = UserPermissionError("Access denied")
        
        assert todo_permission.status_code == 403
        assert user_permission.status_code == 403
        
        # All validation errors should have 400
        invalid_operation = InvalidTodoOperationError("Invalid operation")
        ai_invalid_request = AIInvalidRequestError("Invalid request")
        
        assert invalid_operation.status_code == 400
        assert ai_invalid_request.status_code == 400


class TestExceptionHTTPCompatibility:
    """Test that exceptions work properly with FastAPI/HTTP standards."""

    def test_exception_http_detail_format(self):
        """Test that exception detail follows expected HTTP format."""
        exc = TodoNotFoundError("Todo not found", details={"todo_id": "123"})
        
        # Should have the structure expected by FastAPI
        assert isinstance(exc.detail, dict)
        assert "message" in exc.detail
        assert "error_code" in exc.detail
        assert "details" in exc.detail
        
        assert exc.detail["message"] == "Todo not found"
        assert exc.detail["error_code"] == "TODO_NOT_FOUND"
        assert exc.detail["details"]["todo_id"] == "123"

    def test_exception_as_http_exception(self):
        """Test that custom exceptions behave as HTTP exceptions."""
        exc = AIQuotaExceededError("Quota exceeded")
        
        # Should be usable as HTTPException
        assert hasattr(exc, 'status_code')
        assert hasattr(exc, 'detail')
        assert exc.status_code == 429
        
        # Should be raisable in FastAPI context
        with pytest.raises(HTTPException) as exc_info:
            raise exc
        
        assert exc_info.value.status_code == 429
```

```

