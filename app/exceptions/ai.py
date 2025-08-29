# ruff: noqa: D107
"""AI service exceptions."""

from typing import Any

from .base import BaseAppException


class AIServiceError(BaseAppException):
    """Base exception for AI service errors."""

    def __init__(
        self,
        message: str = "AI service error occurred",
        error_code: str = "AI_SERVICE_ERROR",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, error_code, details)


class AIServiceUnavailableError(AIServiceError):
    """Exception raised when AI service is unavailable."""

    def __init__(
        self,
        message: str = "AI service is temporarily unavailable",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, "AI_SERVICE_UNAVAILABLE", details)


class AIQuotaExceededError(AIServiceError):
    """Exception raised when AI service quota is exceeded."""

    def __init__(
        self,
        message: str = "AI service quota exceeded",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, "AI_QUOTA_EXCEEDED", details)


class AIInvalidRequestError(AIServiceError):
    """Exception raised for invalid AI service requests."""

    def __init__(
        self,
        message: str = "Invalid request to AI service",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, "AI_INVALID_REQUEST", details)


class AITimeoutError(AIServiceError):
    """Exception raised when AI service request times out."""

    def __init__(
        self,
        message: str = "AI service request timed out",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, "AI_TIMEOUT", details)


class AIParsingError(AIServiceError):
    """Exception raised when AI response cannot be parsed."""

    def __init__(
        self,
        message: str = "Failed to parse AI service response",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, "AI_PARSING_ERROR", details)


class AIConfigurationError(AIServiceError):
    """Exception raised when AI service is not properly configured."""

    def __init__(
        self,
        message: str = "AI service is not properly configured",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, "AI_CONFIGURATION_ERROR", details)


class AIContentFilterError(AIServiceError):
    """Exception raised when content is blocked by AI safety filters."""

    def __init__(
        self,
        message: str = "Content was blocked by AI safety filters",
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message, "AI_CONTENT_FILTERED", details)


class AIRateLimitError(AIServiceError):
    """Exception raised when AI service rate limit is hit."""

    def __init__(
        self,
        message: str = "AI service rate limit exceeded",
        retry_after: int | None = None,
        details: dict[str, Any] | None = None,
    ):
        if details is None:
            details = {}
        if retry_after:
            details["retry_after"] = retry_after
        super().__init__(message, "AI_RATE_LIMITED", details)


# Map common error patterns to exceptions
AI_ERROR_MAPPING = {
    "quota_exceeded": AIQuotaExceededError,
    "service_unavailable": AIServiceUnavailableError,
    "invalid_request": AIInvalidRequestError,
    "timeout": AITimeoutError,
    "parsing_error": AIParsingError,
    "configuration_error": AIConfigurationError,
    "content_filtered": AIContentFilterError,
    "rate_limited": AIRateLimitError,
}


def map_ai_error(
    error_type: str, message: str, details: dict[str, Any] | None = None
) -> AIServiceError:
    """Map error type to appropriate exception."""
    exception_class = AI_ERROR_MAPPING.get(error_type, AIServiceError)
    return exception_class(message, details)
