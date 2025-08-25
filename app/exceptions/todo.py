"""Todo-related exceptions."""

from fastapi import HTTPException
from .base import BaseAppException


class TodoNotFoundError(BaseAppException):
    """Raised when a todo is not found."""

    def __init__(self, message: str = "Todo not found"):
        super().__init__(message=message, status_code=404, error_code="TODO_NOT_FOUND")


class TodoPermissionError(BaseAppException):
    """Raised when user doesn't have permission to access a todo."""

    def __init__(self, message: str = "You don't have permission to access this todo"):
        super().__init__(message=message, status_code=403, error_code="TODO_PERMISSION_DENIED")


class InvalidTodoOperationError(BaseAppException):
    """Raised when an invalid operation is performed on a todo."""

    def __init__(self, message: str = "Invalid todo operation"):
        super().__init__(message=message, status_code=400, error_code="INVALID_TODO_OPERATION")


class MaxTodoDepthExceededError(BaseAppException):
    """Raised when todo nesting depth exceeds maximum allowed."""

    def __init__(self, message: str = "Maximum todo nesting depth exceeded"):
        super().__init__(message=message, status_code=400, error_code="MAX_TODO_DEPTH_EXCEEDED")


class TodoValidationError(BaseAppException):
    """Raised when todo data validation fails."""

    def __init__(self, message: str = "Todo validation failed"):
        super().__init__(message=message, status_code=422, error_code="TODO_VALIDATION_ERROR")


class DuplicateTodoError(BaseAppException):
    """Raised when attempting to create a duplicate todo."""

    def __init__(self, message: str = "Todo with this title already exists"):
        super().__init__(message=message, status_code=409, error_code="DUPLICATE_TODO")
