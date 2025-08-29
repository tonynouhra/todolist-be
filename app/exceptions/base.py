# ruff: noqa: D107
"""Base exception classes."""

from typing import Any

from fastapi import HTTPException


class BaseAppException(HTTPException):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: dict[str, Any] | None = None,
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}

        super().__init__(
            status_code=status_code,
            detail={"message": message, "error_code": error_code, "details": details},
        )


class NotFoundError(BaseAppException):
    """Exception raised when a resource is not found."""

    def __init__(
        self,
        message: str = "Resource not found",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message=message, status_code=404, error_code="NOT_FOUND", details=details)


class AppPermissionError(BaseAppException):
    """Exception raised when user doesn't have permission to access a resource."""

    def __init__(
        self,
        message: str = "Permission denied",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            status_code=403,
            error_code="PERMISSION_DENIED",
            details=details,
        )


class ValidationError(BaseAppException):
    """Exception raised when validation fails."""

    def __init__(
        self,
        message: str = "Validation failed",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(
            message=message,
            status_code=422,
            error_code="VALIDATION_ERROR",
            details=details,
        )
