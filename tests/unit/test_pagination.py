"""
Unit tests for Pagination utilities.

This module contains comprehensive unit tests for the pagination utility functions
and classes used throughout the application.
"""

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.shared.pagination import PaginatedResponse, PaginationParams, paginate

# Create a test base for SQLAlchemy models
Base = declarative_base()


class TestPaginationParams:
    """Test cases for PaginationParams."""

    def test_default_values(self):
        """Test default pagination parameters."""
        params = PaginationParams()
        
        assert params.page == 1
        assert params.size == 20

    def test_custom_values(self):
        """Test custom pagination parameters."""
        params = PaginationParams(page=3, size=50)
        
        assert params.page == 3
        assert params.size == 50

    def test_validation_minimum_page(self):
        """Test minimum page validation."""
        with pytest.raises(ValueError):
            PaginationParams(page=0)
        
        with pytest.raises(ValueError):
            PaginationParams(page=-1)

    def test_validation_minimum_size(self):
        """Test minimum size validation."""
        with pytest.raises(ValueError):
            PaginationParams(size=0)
        
        with pytest.raises(ValueError):
            PaginationParams(size=-1)

    def test_validation_maximum_size(self):
        """Test maximum size validation."""
        with pytest.raises(ValueError):
            PaginationParams(size=101)  # Max is 100
        
        # Should work with exactly 100
        params = PaginationParams(size=100)
        assert params.size == 100

    def test_validation_valid_edge_cases(self):
        """Test valid edge case values."""
        # Minimum valid values
        params = PaginationParams(page=1, size=1)
        assert params.page == 1
        assert params.size == 1
        
        # Maximum valid size
        params = PaginationParams(page=1, size=100)
        assert params.page == 1
        assert params.size == 100


class TestPaginatedResponse:
    """Test cases for PaginatedResponse."""

    def test_paginated_response_creation(self):
        """Test creating a paginated response."""
        items = ["item1", "item2", "item3"]
        response = PaginatedResponse[str](
            items=items,
            total=25,
            page=2,
            size=10,
            has_next=True,
            has_prev=True,
            total_pages=3
        )
        
        assert response.items == items
        assert response.total == 25
        assert response.page == 2
        assert response.size == 10
        assert response.has_next is True
        assert response.has_prev is True
        assert response.total_pages == 3

    def test_paginated_response_with_empty_items(self):
        """Test paginated response with empty items."""
        response = PaginatedResponse[str](
            items=[],
            total=0,
            page=1,
            size=10,
            has_next=False,
            has_prev=False,
            total_pages=0
        )
        
        assert response.items == []
        assert response.total == 0
        assert response.has_next is False
        assert response.has_prev is False

    def test_paginated_response_type_safety(self):
        """Test type safety of paginated response."""
        # Test with integers
        int_response = PaginatedResponse[int](
            items=[1, 2, 3],
            total=3,
            page=1,
            size=10,
            has_next=False,
            has_prev=False,
            total_pages=1
        )
        assert all(isinstance(item, int) for item in int_response.items)
        
        # Test with dictionaries
        dict_items = [{"id": 1, "name": "test"}]
        dict_response = PaginatedResponse[dict](
            items=dict_items,
            total=1,
            page=1,
            size=10,
            has_next=False,
            has_prev=False,
            total_pages=1
        )
        assert all(isinstance(item, dict) for item in dict_response.items)


class TestPaginateFunction:
    """Test cases for paginate function."""

    @pytest.mark.asyncio
    async def test_paginate_empty_result(self, test_db):
        """Test pagination with empty result set."""
        # Create a query that returns no results
        query = select(1).where(1 == 0)  # Always false condition
        params = PaginationParams(page=1, size=10)
        
        result = await paginate(test_db, query, params)
        
        assert result["total"] == 0
        assert result["items"] == []
        assert result["page"] == 1
        assert result["size"] == 10
        assert result["has_next"] is False
        assert result["has_prev"] is False
        assert result["total_pages"] == 0

    @pytest.mark.asyncio
    async def test_paginate_single_page(self, test_db):
        """Test pagination with single page of results."""
        # Create test data
        from models.todo import Todo
        
        # Create 5 todos
        todos = []
        for i in range(5):
            todo = Todo(
                title=f"Todo {i}",
                status="todo",
                priority=3,
                user_id="test_user_id"
            )
            test_db.add(todo)
            todos.append(todo)
        
        await test_db.commit()
        
        # Test pagination
        query = select(Todo)
        params = PaginationParams(page=1, size=10)
        
        result = await paginate(test_db, query, params)
        
        assert result["total"] == 5
        assert len(result["items"]) == 5
        assert result["page"] == 1
        assert result["size"] == 10
        assert result["has_next"] is False
        assert result["has_prev"] is False
        assert result["total_pages"] == 1

    @pytest.mark.asyncio
    async def test_paginate_multiple_pages(self, test_db):
        """Test pagination with multiple pages."""
        from models.todo import Todo
        
        # Create 25 todos
        todos = []
        for i in range(25):
            todo = Todo(
                title=f"Todo {i}",
                status="todo",
                priority=3,
                user_id="test_user_id"
            )
            test_db.add(todo)
            todos.append(todo)
        
        await test_db.commit()
        
        # Test first page
        query = select(Todo)
        params = PaginationParams(page=1, size=10)
        
        result = await paginate(test_db, query, params)
        
        assert result["total"] == 25
        assert len(result["items"]) == 10
        assert result["page"] == 1
        assert result["size"] == 10
        assert result["has_next"] is True
        assert result["has_prev"] is False
        assert result["total_pages"] == 3

    @pytest.mark.asyncio
    async def test_paginate_middle_page(self, test_db):
        """Test pagination with middle page."""
        from models.todo import Todo
        
        # Create 25 todos
        for i in range(25):
            todo = Todo(
                title=f"Todo {i}",
                status="todo",
                priority=3,
                user_id="test_user_id"
            )
            test_db.add(todo)
        
        await test_db.commit()
        
        # Test middle page
        query = select(Todo)
        params = PaginationParams(page=2, size=10)
        
        result = await paginate(test_db, query, params)
        
        assert result["total"] == 25
        assert len(result["items"]) == 10
        assert result["page"] == 2
        assert result["size"] == 10
        assert result["has_next"] is True
        assert result["has_prev"] is True
        assert result["total_pages"] == 3

    @pytest.mark.asyncio
    async def test_paginate_last_page(self, test_db):
        """Test pagination with last page."""
        from models.todo import Todo
        
        # Create 25 todos
        for i in range(25):
            todo = Todo(
                title=f"Todo {i}",
                status="todo",
                priority=3,
                user_id="test_user_id"
            )
            test_db.add(todo)
        
        await test_db.commit()
        
        # Test last page
        query = select(Todo)
        params = PaginationParams(page=3, size=10)
        
        result = await paginate(test_db, query, params)
        
        assert result["total"] == 25
        assert len(result["items"]) == 5  # Last page has 5 items
        assert result["page"] == 3
        assert result["size"] == 10
        assert result["has_next"] is False
        assert result["has_prev"] is True
        assert result["total_pages"] == 3

    @pytest.mark.asyncio
    async def test_paginate_page_beyond_range(self, test_db):
        """Test pagination with page beyond available data."""
        from models.todo import Todo
        
        # Create 5 todos
        for i in range(5):
            todo = Todo(
                title=f"Todo {i}",
                status="todo",
                priority=3,
                user_id="test_user_id"
            )
            test_db.add(todo)
        
        await test_db.commit()
        
        # Test page beyond range
        query = select(Todo)
        params = PaginationParams(page=10, size=10)
        
        result = await paginate(test_db, query, params)
        
        assert result["total"] == 5
        assert len(result["items"]) == 0  # No items on page 10
        assert result["page"] == 10
        assert result["size"] == 10
        assert result["has_next"] is False
        assert result["has_prev"] is True
        assert result["total_pages"] == 1

    @pytest.mark.asyncio
    async def test_paginate_custom_page_size(self, test_db):
        """Test pagination with custom page size."""
        from models.todo import Todo
        
        # Create 15 todos
        for i in range(15):
            todo = Todo(
                title=f"Todo {i}",
                status="todo",
                priority=3,
                user_id="test_user_id"
            )
            test_db.add(todo)
        
        await test_db.commit()
        
        # Test with page size of 3
        query = select(Todo)
        params = PaginationParams(page=2, size=3)
        
        result = await paginate(test_db, query, params)
        
        assert result["total"] == 15
        assert len(result["items"]) == 3
        assert result["page"] == 2
        assert result["size"] == 3
        assert result["has_next"] is True
        assert result["has_prev"] is True
        assert result["total_pages"] == 5

    @pytest.mark.asyncio
    async def test_paginate_with_filtering(self, test_db):
        """Test pagination with filtered query."""
        from models.todo import Todo
        
        # Create todos with different statuses
        for i in range(10):
            status = "done" if i < 3 else "todo"
            todo = Todo(
                title=f"Todo {i}",
                status=status,
                priority=3,
                user_id="test_user_id"
            )
            test_db.add(todo)
        
        await test_db.commit()
        
        # Test pagination with filter
        query = select(Todo).where(Todo.status == "done")
        params = PaginationParams(page=1, size=5)
        
        result = await paginate(test_db, query, params)
        
        assert result["total"] == 3  # Only 3 "done" todos
        assert len(result["items"]) == 3
        assert result["page"] == 1
        assert result["size"] == 5
        assert result["has_next"] is False
        assert result["has_prev"] is False
        assert result["total_pages"] == 1

    @pytest.mark.asyncio
    async def test_paginate_total_pages_calculation(self, test_db):
        """Test total pages calculation edge cases."""
        from models.todo import Todo
        
        # Test exact multiple
        for i in range(20):  # Exactly 2 pages of 10
            todo = Todo(
                title=f"Todo {i}",
                status="todo",
                priority=3,
                user_id="test_user_id"
            )
            test_db.add(todo)
        
        await test_db.commit()
        
        query = select(Todo)
        params = PaginationParams(page=1, size=10)
        
        result = await paginate(test_db, query, params)
        
        assert result["total"] == 20
        assert result["total_pages"] == 2
        assert result["has_next"] is True
        
        # Test page 2
        params = PaginationParams(page=2, size=10)
        result = await paginate(test_db, query, params)
        
        assert result["page"] == 2
        assert result["has_next"] is False
        assert len(result["items"]) == 10
```

```python:/Users/tonynouhra/Documents/MyProjects/TodoList/todolist-be/tests/unit/test_exceptions.py
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

```python:/Users/tonynouhra/Documents/MyProjects/TodoList/todolist-be/tests/unit/test_dependencies.py
"""
Unit tests for Dependencies module.

This module contains comprehensive unit tests for the dependency injection
functions used throughout the application.
"""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, validate_token
from app.domains.user.service import UserService
from models.user import User


class TestValidateToken:
    """Test cases for validate_token dependency."""

    @pytest.mark.asyncio
    async def test_validate_token_success(self):
        """Test successful token validation."""
        mock_token = MagicMock()
        mock_token.credentials = "valid_jwt_token"
        
        mock_payload = {
            "sub": "user_123",
            "email": "test@example.com",
            "username": "testuser"
        }
        
        with patch('app.core.dependencies.auth.verify_token') as mock_verify:
            mock_verify.return_value = mock_payload
            
            result = await validate_token(mock_token)
            
            assert result == mock_payload
            mock_verify.assert_called_once_with("valid_jwt_token")

    @pytest.mark.asyncio
    async def test_validate_token_none_token(self):
        """Test token validation with None token."""
        with pytest.raises(HTTPException) as exc_info:
            await validate_token(None)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Authentication token is required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_validate_token_empty_credentials(self):
        """Test token validation with empty credentials."""
        mock_token = MagicMock()
        mock_token.credentials = ""
        
        with pytest.raises(HTTPException) as exc_info:
            await validate_token(mock_token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Authentication token is required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_validate_token_none_credentials(self):
        """Test token validation with None credentials."""
        mock_token = MagicMock()
        mock_token.credentials = None
        
        with pytest.raises(HTTPException) as exc_info:
            await validate_token(mock_token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Authentication token is required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_validate_token_verification_failure(self):
        """Test token validation when verification fails."""
        mock_token = MagicMock()
        mock_token.credentials = "invalid_token"
        
        with patch('app.core.dependencies.auth.verify_token') as mock_verify:
            mock_verify.return_value = None
            
            with pytest.raises(HTTPException) as exc_info:
                await validate_token(mock_token)
            
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Invalid authentication token" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_validate_token_verification_exception(self):
        """Test token validation when verification raises exception."""
        mock_token = MagicMock()
        mock_token.credentials = "problematic_token"
        
        with patch('app.core.dependencies.auth.verify_token') as mock_verify:
            mock_verify.side_effect = Exception("Verification error")
            
            with patch('app.core.dependencies.logger') as mock_logger:
                with pytest.raises(HTTPException) as exc_info:
                    await validate_token(mock_token)
                
                assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
                assert "Authentication failed" in exc_info.value.detail
                mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_token_http_exception_passthrough(self):
        """Test that HTTPException from auth is passed through."""
        mock_token = MagicMock()
        mock_token.credentials = "expired_token"
        
        original_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
        
        with patch('app.core.dependencies.auth.verify_token') as mock_verify:
            mock_verify.side_effect = original_exception
            
            with pytest.raises(HTTPException) as exc_info:
                await validate_token(mock_token)
            
            # Should be the same exception
            assert exc_info.value is original_exception

    @pytest.mark.asyncio
    async def test_validate_token_www_authenticate_header(self):
        """Test that WWW-Authenticate header is set correctly."""
        mock_token = MagicMock()
        mock_token.credentials = None
        
        with pytest.raises(HTTPException) as exc_info:
            await validate_token(mock_token)
        
        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}


class TestGetCurrentUser:
    """Test cases for get_current_user dependency."""

    @pytest.mark.asyncio
    async def test_get_current_user_success(self, test_db):
        """Test successful user retrieval."""
        mock_request = MagicMock(spec=Request)
        mock_payload = {
            "sub": "clerk_user_123",
            "email": "test@example.com",
            "username": "testuser"
        }
        
        # Create a test user
        test_user = User(
            clerk_user_id="clerk_user_123",
            email="test@example.com",
            username="testuser",
            is_active=True
        )
        test_db.add(test_user)
        await test_db.commit()
        await test_db.refresh(test_user)
        
        result = await get_current_user(mock_request, mock_payload, test_db)
        
        assert result is not None
        assert result.clerk_user_id == "clerk_user_123"
        assert result.email == "test@example.com"
        assert result.username == "testuser"

    @pytest.mark.asyncio
    async def test_get_current_user_not_found(self, test_db):
        """Test user retrieval when user doesn't exist."""
        mock_request = MagicMock(spec=Request)
        mock_payload = {
            "sub": "nonexistent_user",
            "email": "notfound@example.com",
            "username": "notfound"
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request, mock_payload, test_db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "User not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_creates_new_user(self, test_db):
        """Test that new user is created when not found."""
        mock_request = MagicMock(spec=Request)
        mock_payload = {
            "sub": "new_clerk_user",
            "email": "newuser@example.com",
            "username": "newuser"
        }
        
        # Mock UserService to simulate user creation
        with patch('app.core.dependencies.UserService') as mock_user_service_class:
            mock_user_service = mock_user_service_class.return_value
            
            # First call returns None (user not found)
            # Second call returns the created user
            new_user = User(
                clerk_user_id="new_clerk_user",
                email="newuser@example.com",
                username="newuser",
                is_active=True
            )
            
            mock_user_service.get_user_by_clerk_id.return_value = None
            mock_user_service.create_user_from_clerk.return_value = new_user
            
            result = await get_current_user(mock_request, mock_payload, test_db)
            
            assert result == new_user
            mock_user_service.get_user_by_clerk_id.assert_called_once_with("new_clerk_user")
            mock_user_service.create_user_from_clerk.assert_called_once_with(mock_payload)

    @pytest.mark.asyncio
    async def test_get_current_user_inactive_user(self, test_db):
        """Test user retrieval with inactive user."""
        mock_request = MagicMock(spec=Request)
        mock_payload = {
            "sub": "inactive_user",
            "email": "inactive@example.com",
            "username": "inactive"
        }
        
        # Create an inactive test user
        test_user = User(
            clerk_user_id="inactive_user",
            email="inactive@example.com",
            username="inactive",
            is_active=False
        )
        test_db.add(test_user)
        await test_db.commit()
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request, mock_payload, test_db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "User account is inactive" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_missing_sub_in_payload(self, test_db):
        """Test user retrieval with missing 'sub' in payload."""
        mock_request = MagicMock(spec=Request)
        mock_payload = {
            "email": "test@example.com",
            "username": "testuser"
            # Missing 'sub' field
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request, mock_payload, test_db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid token payload" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_database_error(self, test_db):
        """Test user retrieval with database error."""
        mock_request = MagicMock(spec=Request)
        mock_payload = {
            "sub": "user_123",
            "email": "test@example.com",
            "username": "testuser"
        }
        
        with patch('app.core.dependencies.UserService') as mock_user_service_class:
            mock_user_service = mock_user_service_class.return_value
            mock_user_service.get_user_by_clerk_id.side_effect = Exception("Database error")
            
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_request, mock_payload, test_db)
            
            assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Authentication service error" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_user_service_integration(self, test_db):
        """Test integration with UserService."""
        mock_request = MagicMock(spec=Request)
        mock_payload = {
            "sub": "integration_user",
            "email": "integration@example.com",
            "username": "integration"
        }
        
        # Create a real UserService instance
        user_service = UserService(test_db)
        
        with patch('app.core.dependencies.UserService') as mock_user_service_class:
            mock_user_service_class.return_value = user_service
            
            # Create user first
            created_user = await user_service.create_user_from_clerk(mock_payload)
            
            # Now test retrieval
            result = await get_current_user(mock_request, mock_payload, test_db)
            
            assert result.clerk_user_id == created_user.clerk_user_id
            assert result.email == created_user.email
            assert result.username == created_user.username

    @pytest.mark.asyncio
    async def test_get_current_user_request_state_preservation(self, test_db):
        """Test that request state is preserved during user retrieval."""
        mock_request = MagicMock(spec=Request)
        mock_request.state.request_id = "req_123"
        mock_request.state.user_agent = "TestAgent/1.0"
        
        mock_payload = {
            "sub": "state_test_user",
            "email": "state@example.com",
            "username": "stateuser"
        }
        
        # Create user
        test_user = User(
            clerk_user_id="state_test_user",
            email="state@example.com",
            username="stateuser",
            is_active=True
        )
        test_db.add(test_user)
        await test_db.commit()
        
        result = await get_current_user(mock_request, mock_payload, test_db)
        
        # Request state should be preserved
        assert mock_request.state.request_id == "req_123"
        assert mock_request.state.user_agent == "TestAgent/1.0"
        assert result is not None


class TestDependencyIntegration:
    """Test integration between dependencies."""

    @pytest.mark.asyncio
    async def test_full_authentication_flow(self, test_db):
        """Test complete authentication flow from token to user."""
        # Mock JWT token
        mock_token = MagicMock()
        mock_token.credentials = "valid_jwt_token"
        
        mock_payload = {
            "sub": "flow_test_user",
            "email": "flow@example.com",
            "username": "flowuser"
        }
        
        # Create user for the flow
        test_user = User(
            clerk_user_id="flow_test_user",
            email="flow@example.com",
            username="flowuser",
            is_active=True
        )
        test_db.add(test_user)
        await test_db.commit()
        
        mock_request = MagicMock(spec=Request)
        
        with patch('app.core.dependencies.auth.verify_token') as mock_verify:
            mock_verify.return_value = mock_payload
            
            # Step 1: Validate token
            validated_payload = await validate_token(mock_token)
            assert validated_payload == mock_payload
            
            # Step 2: Get current user
            current_user = await get_current_user(mock_request, validated_payload, test_db)
            assert current_user.clerk_user_id == "flow_test_user"
            assert current_user.email == "flow@example.com"
            assert current_user.username == "flowuser"

    def test_security_bearer_configuration(self):
        """Test HTTPBearer security configuration."""
        from app.core.dependencies import security
        
        assert isinstance(security, HTTPBearer)
        # HTTPBearer should be configured properly for the dependency injection
```

```python:/Users/tonynouhra/Documents/MyProjects/TodoList/todolist-be/tests/unit/test_main_app.py
"""
Unit tests for Main Application module.

This module contains comprehensive unit tests for the main FastAPI application,
middleware, exception handlers, and application lifecycle.
"""

import json
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from httpx import AsyncClient
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.main import (
    app,
    create_app,
    setup_exception_handlers,
    setup_middleware,
    setup_routers,
)


class TestAppCreation:
    """Test cases for FastAPI application creation."""

    def test_create_app_returns_fastapi_instance(self):
        """Test that create_app returns a FastAPI instance."""
        test_app = create_app()
        
        assert test_app.title == "AI Todo List API"
        assert test_app.description == "Intelligent task management system with AI-powered sub-task generation"
        assert test_app.version == "1.0.0"

    def test_app_docs_configuration_development(self):
        """Test docs configuration in development mode."""
        with patch('app.main.settings') as mock_settings:
            mock_settings.environment = "development"
            
            test_app = create_app()
            
            # In development, docs should be available
            assert test_app.docs_url == "/docs"
            assert test_app.redoc_url == "/redoc"

    def test_app_docs_configuration_production(self):
        """Test docs configuration in production mode."""
        with patch('app.main.settings') as mock_settings:
            mock_settings.environment = "production"
            
            test_app = create_app()
            
            # In production, docs should be disabled
            assert test_app.docs_url is None
            assert test_app.redoc_url is None

    def test_app_components_setup(self):
        """Test that all app components are set up correctly."""
        with patch('app.main.setup_middleware') as mock_middleware:
            with patch('app.main.setup_exception_handlers') as mock_handlers:
                with patch('app.main.setup_routers') as mock_routers:
                    
                    test_app = create_app()
                    
                    mock_middleware.assert_called_once_with(test_app)
                    mock_handlers.assert_called_once_with(test_app)
                    mock_routers.assert_called_once_with(test_app)


class TestMiddleware:
    """Test cases for application middleware."""

    @pytest.mark.asyncio
    async def test_cors_middleware_configuration(self):
        """Test CORS middleware is configured correctly."""
        with TestClient(app) as client:
            # Test preflight request
            response = client.options(
                "/api/todos/",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Content-Type,Authorization"
                }
            )
            
            # Should allow CORS
            assert "access-control-allow-origin" in response.headers

    @pytest.mark.asyncio
    async def test_request_id_middleware(self, client: AsyncClient):
        """Test request ID middleware adds request ID header."""
        response = await client.get("/health")
        
        assert "X-Request-ID" in response.headers
        # Should be a valid UUID
        request_id = response.headers["X-Request-ID"]
        assert uuid.UUID(request_id)  # Will raise if not valid UUID

    @pytest.mark.asyncio
    async def test_request_id_middleware_different_requests(self, client: AsyncClient):
        """Test that different requests get different request IDs."""
        response1 = await client.get("/health")
        response2 = await client.get("/health")
        
        request_id1 = response1.headers["X-Request-ID"]
        request_id2 = response2.headers["X-Request-ID"]
        
        assert request_id1 != request_id2

    def test_setup_middleware_called_during_app_creation(self):
        """Test that setup_middleware is called during app creation."""
        mock_app = MagicMock()
        
        setup_middleware(mock_app)
        
        # Should add CORS middleware
        mock_app.add_middleware.assert_called()
        
        # Should add request ID middleware
        mock_app.middleware.assert_called_with("http")


class TestExceptionHandlers:
    """Test cases for application exception handlers."""

    @pytest.mark.asyncio
    async def test_http_exception_handler(self, client: AsyncClient):
        """Test HTTP exception handler."""
        # Trigger a 404 by accessing non-existent endpoint
        response = await client.get("/nonexistent-endpoint")
        
        assert response.status_code == 404
        data = response.json()
        
        assert data["status"] == "error"
        assert "message" in data
        assert "timestamp" in data
        # Request ID should be included if middleware is working
        assert "request_id" in data

    @pytest.mark.asyncio
    async def test_validation_exception_handler(self, client: AsyncClient):
        """Test validation exception handler."""
        # Send invalid data to trigger validation error
        response = await client.post(
            "/api/todos/",
            json={"invalid_field": "value"},  # Missing required fields
            headers={"Authorization": "Bearer fake_token"}
        )
        
        assert response.status_code == 422
        data = response.json()
        
        assert data["status"] == "error"
        assert data["message"] == "Validation error"
        assert "details" in data
        assert "timestamp" in data

    def test_setup_exception_handlers_registration(self):
        """Test that exception handlers are properly registered."""
        mock_app = MagicMock()
        
        setup_exception_handlers(mock_app)
        
        # Should register exception handlers
        assert mock_app.exception_handler.call_count >= 2
        
        # Check that both StarletteHTTPException and RequestValidationError handlers are registered
        call_args_list = mock_app.exception_handler.call_args_list
        exception_types = [call[0][0] for call in call_args_list]
        
        assert StarletteHTTPException in exception_types
        assert RequestValidationError in exception_types


class TestHealthEndpoint:
    """Test cases for health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, client: AsyncClient):
        """Test successful health check."""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] in ["healthy", "degraded"]
        assert data["version"] == "1.0.0"
        assert "environment" in data
        assert "timestamp" in data
        assert "services" in data
        assert "database" in data["services"]

    @pytest.mark.asyncio
    async def test_health_check_database_status(self, client: AsyncClient):
        """Test health check database status."""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Database status should be reported
        assert data["services"]["database"] in ["healthy", "unhealthy"]

    @pytest.mark.asyncio
    async def test_health_check_ai_service_status(self, client: AsyncClient):
        """Test health check AI service status."""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # AI service status should be reported
        assert data["services"]["ai_service"] in ["healthy", "unhealthy", "not_configured"]

    @pytest.mark.asyncio
    async def test_health_check_with_database_error(self, client: AsyncClient):
        """Test health check when database is unhealthy."""
        with patch('app.main.get_db') as mock_get_db:
            mock_db = AsyncMock()
            mock_db.execute.side_effect = Exception("Database connection failed")
            mock_get_db.return_value = mock_db
            
            response = await client.get("/health")
            
            # Should still return 200 but with degraded status
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"
            assert data["services"]["database"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_health_check_ai_service_error(self, client: AsyncClient):
        """Test health check when AI service check fails."""
        with patch('app.main.settings') as mock_settings:
            mock_settings.has_ai_enabled = True
            
            with patch('app.domains.ai.service.AIService') as mock_ai_service:
                mock_ai_service.return_value.get_service_status.side_effect = Exception("AI service error")
                
                response = await client.get("/health")
                
                assert response.status_code == 200
                data = response.json()
                assert data["services"]["ai_service"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_health_check_complete_failure(self, client: AsyncClient):
        """Test health check when everything fails."""
        with patch('app.main.get_db') as mock_get_db:
            mock_get_db.side_effect = Exception("Complete failure")
            
            response = await client.get("/health")
            
            # Should return 503 for complete failure
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "unhealthy"
            assert "Health check failed" in data["message"]


class TestRootEndpoint:
    """Test cases for root endpoint."""

    @pytest.mark.asyncio
    async def test_root_endpoint_development(self, client: AsyncClient):
        """Test root endpoint in development mode."""
        with patch('app.main.settings') as mock_settings:
            mock_settings.environment = "development"
            
            response = await client.get("/")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["name"] == "AI Todo List API"
            assert data["version"] == "1.0.0"
            assert data["description"] == "Intelligent task management with AI assistance"
            assert data["docs_url"] == "/docs"

    @pytest.mark.asyncio
    async def test_root_endpoint_production(self, client: AsyncClient):
        """Test root endpoint in production mode."""
        with patch('app.main.settings') as mock_settings:
            mock_settings.environment = "production"
            
            response = await client.get("/")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["name"] == "AI Todo List API"
            assert data["version"] == "1.0.0"
            assert data["docs_url"] is None


class TestRouterSetup:
    """Test cases for router setup."""

    def test_setup_routers_includes_all_domains(self):
        """Test that all domain routers are included."""
        mock_app = MagicMock()
        
        with patch('app.domains.user.controller.router') as mock_user_router:
            with patch('app.domains.todo.controller.router') as mock_todo_router:
                with patch('app.domains.project.controller.router') as mock_project_router:
                    with patch('app.domains.ai.controller.router') as mock_ai_router:
                        
                        setup_routers(mock_app)
                        
                        # All routers should be included
                        mock_app.include_router.assert_any_call(mock_user_router)
                        mock_app.include_router.assert_any_call(mock_todo_router)
                        mock_app.include_router.assert_any_call(mock_project_router)
                        mock_app.include_router.assert_any_call(mock_ai_router)

    @pytest.mark.asyncio
    async def test_router_endpoints_accessible(self, client: AsyncClient):
        """Test that router endpoints are accessible."""
        # Test that main domain endpoints exist (will return 401 without auth, but that's expected)
        
        # User endpoints
        response = await client.get("/api/users/profile")
        assert response.status_code in [200, 401, 422]  # Any of these is fine - means endpoint exists
        
        # Todo endpoints  
        response = await client.get("/api/todos/")
        assert response.status_code in [200, 401, 422]
        
        # AI endpoints
        response = await client.get("/api/ai/status")
        assert response.status_code in [200, 401, 422]


class TestApplicationLifespan:
    """Test cases for application lifespan management."""

    @pytest.mark.asyncio
    async def test_lifespan_startup_development(self):
        """Test application startup in development mode."""
        with patch('app.main.settings') as mock_settings:
            mock_settings.environment = "development"
            
            with patch('app.main.engine') as mock_engine:
                mock_conn = AsyncMock()
                mock_engine.begin.return_value.__aenter__.return_value = mock_conn
                
                # Test lifespan context manager
                from app.main import lifespan
                
                test_app = MagicMock()
                async with lifespan(test_app):
                    # During startup, tables should be created in development
                    mock_engine.begin.assert_called_once()
                
                # During shutdown, engine should be disposed
                mock_engine.dispose.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_startup_production(self):
        """Test application startup in production mode."""
        with patch('app.main.settings') as mock_settings:
            mock_settings.environment = "production"
            
            with patch('app.main.engine') as mock_engine:
                from app.main import lifespan
                
                test_app = MagicMock()
                async with lifespan(test_app):
                    # In production, tables should NOT be auto-created
                    mock_engine.begin.assert_not_called()
                
                # Engine should still be disposed on shutdown
                mock_engine.dispose.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_exception_handling(self):
        """Test lifespan exception handling."""
        with patch('app.main.engine') as mock_engine:
            mock_engine.dispose.side_effect = Exception("Disposal error")
            
            from app.main import lifespan
            
            test_app = MagicMock()
            
            # Should not raise exception even if disposal fails
            try:
                async with lifespan(test_app):
                    pass
            except Exception:
                pytest.fail("Lifespan should handle disposal exceptions gracefully")


class TestApplicationConfiguration:
    """Test cases for application configuration."""

    def test_app_instance_is_configured(self):
        """Test that the main app instance is properly configured."""
        assert app.title == "AI Todo List API"
        assert app.version == "1.0.0"
        
        # Should have routes registered
        routes = [route.path for route in app.routes]
        assert "/" in routes
        assert "/health" in routes

    def test_app_middleware_configured(self):
        """Test that middleware is configured on the main app."""
        # Check that middleware is present
        middleware_types = [type(middleware) for middleware in app.user_middleware]
        
        # CORS middleware should be present
        from fastapi.middleware.cors import CORSMiddleware
        assert any(issubclass(mw_type, CORSMiddleware) for mw_type in middleware_types)

    def test_app_exception_handlers_configured(self):
        """Test that exception handlers are configured on the main app."""
        # Check that exception handlers are registered
        assert StarletteHTTPException in app.exception_handlers
        assert RequestValidationError in app.exception_handlers
```

```

