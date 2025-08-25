"""AI API controller with FastAPI endpoints."""

import logging
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Body, Request, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_current_user, validate_token
from app.domains.ai.service import AIService
from app.schemas.ai import (
    SubtaskGenerationRequest,
    SubtaskGenerationResponse,
    FileAnalysisRequest,
    FileAnalysisResponse,
    AIServiceStatus,
    AIErrorResponse,
)
from app.schemas.base import ResponseSchema
from app.exceptions.ai import (
    AIServiceError,
    AIServiceUnavailableError,
    AIQuotaExceededError,
    AITimeoutError,
    AIConfigurationError,
    AIRateLimitError,
)
from models.user import User


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/ai",
    tags=["ai"],
    dependencies=[Depends(validate_token)],  # Global token validation for all routes
)


@router.post("/generate-subtasks", response_model=ResponseSchema, status_code=201)
async def generate_subtasks(
    request: Request,
    generation_request: SubtaskGenerationRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate AI subtasks for a given task."""

    try:
        service = AIService(db)
        result = await service.generate_subtasks(
            request=generation_request, user_id=current_user.id
        )

        return ResponseSchema(
            status="success",
            message="Subtasks generated successfully",
            data=result.model_dump(),
        )

    except AIConfigurationError as e:
        logger.error(f"AI configuration error: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=ResponseSchema(
                status="error",
                message="AI service is not properly configured",
                data=AIErrorResponse(
                    error_code="AI_CONFIGURATION_ERROR",
                    error_message=str(e),
                    suggestions=[
                        "Check AI service configuration",
                        "Contact administrator",
                    ],
                ).model_dump(),
            ).model_dump(),
        )

    except AIQuotaExceededError as e:
        logger.warning(f"AI quota exceeded: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=ResponseSchema(
                status="error",
                message="AI service quota exceeded",
                data=AIErrorResponse(
                    error_code="AI_QUOTA_EXCEEDED",
                    error_message=str(e),
                    suggestions=[
                        "Try again later",
                        "Upgrade service plan if available",
                    ],
                ).model_dump(),
            ).model_dump(),
        )

    except AIRateLimitError as e:
        logger.warning(f"AI rate limit exceeded: {str(e)}")
        retry_after = getattr(e, "details", {}).get("retry_after", 60)
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"Retry-After": str(retry_after)},
            content=ResponseSchema(
                status="error",
                message="Rate limit exceeded",
                data=AIErrorResponse(
                    error_code="AI_RATE_LIMITED",
                    error_message=str(e),
                    retry_after=retry_after,
                    suggestions=["Wait before making another request"],
                ).model_dump(),
            ).model_dump(),
        )

    except AITimeoutError as e:
        logger.error(f"AI request timeout: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            content=ResponseSchema(
                status="error",
                message="AI request timed out",
                data=AIErrorResponse(
                    error_code="AI_TIMEOUT",
                    error_message=str(e),
                    suggestions=[
                        "Try again with a simpler request",
                        "Check network connectivity",
                    ],
                ).model_dump(),
            ).model_dump(),
        )

    except AIServiceUnavailableError as e:
        logger.error(f"AI service unavailable: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=ResponseSchema(
                status="error",
                message="AI service is temporarily unavailable",
                data=AIErrorResponse(
                    error_code="AI_SERVICE_UNAVAILABLE",
                    error_message=str(e),
                    suggestions=["Try again later", "Check service status"],
                ).model_dump(),
            ).model_dump(),
        )

    except AIServiceError as e:
        logger.error(f"AI service error: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ResponseSchema(
                status="error",
                message="AI service encountered an error",
                data=AIErrorResponse(
                    error_code="AI_SERVICE_ERROR",
                    error_message=str(e),
                    suggestions=[
                        "Try again later",
                        "Contact support if problem persists",
                    ],
                ).model_dump(),
            ).model_dump(),
        )

    except Exception as e:
        logger.error(f"Unexpected error in AI subtask generation: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ResponseSchema(
                status="error", message="An unexpected error occurred", data=None
            ).model_dump(),
        )


@router.post("/analyze-file", response_model=ResponseSchema, status_code=201)
async def analyze_file(
    request: Request,
    analysis_request: FileAnalysisRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Analyze a file using AI."""

    try:
        service = AIService(db)
        result = await service.analyze_file(request=analysis_request, user_id=current_user.id)

        return ResponseSchema(
            status="success",
            message="File analyzed successfully",
            data=result.model_dump(),
        )

    except AIServiceError as e:
        return _handle_ai_service_error(e)
    except Exception as e:
        logger.error(f"Unexpected error in AI file analysis: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ResponseSchema(
                status="error",
                message="An unexpected error occurred during file analysis",
                data=None,
            ).model_dump(),
        )


@router.get("/status", response_model=ResponseSchema)
async def get_ai_service_status(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get AI service status and availability."""

    try:
        service = AIService(db)
        status_info = await service.get_service_status()

        return ResponseSchema(
            status="success",
            message="AI service status retrieved successfully",
            data=status_info.model_dump(),
        )

    except Exception as e:
        logger.error(f"Error getting AI service status: {str(e)}")
        # Return a basic status even if check fails
        return ResponseSchema(
            status="success",
            message="AI service status check failed",
            data=AIServiceStatus(
                service_available=False, model_name="unknown", requests_today=0
            ).model_dump(),
        )


def _handle_ai_service_error(error: AIServiceError) -> JSONResponse:
    """Handle AI service errors with appropriate HTTP status codes."""

    if isinstance(error, AIConfigurationError):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=ResponseSchema(
                status="error",
                message="AI service is not properly configured",
                data=AIErrorResponse(
                    error_code="AI_CONFIGURATION_ERROR",
                    error_message=str(error),
                    suggestions=["Check AI service configuration"],
                ).model_dump(),
            ).model_dump(),
        )
    elif isinstance(error, AIQuotaExceededError):
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=ResponseSchema(
                status="error",
                message="AI service quota exceeded",
                data=AIErrorResponse(
                    error_code="AI_QUOTA_EXCEEDED",
                    error_message=str(error),
                    suggestions=["Try again later", "Upgrade service plan"],
                ).model_dump(),
            ).model_dump(),
        )
    elif isinstance(error, AIRateLimitError):
        retry_after = getattr(error, "details", {}).get("retry_after", 60)
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"Retry-After": str(retry_after)},
            content=ResponseSchema(
                status="error",
                message="Rate limit exceeded",
                data=AIErrorResponse(
                    error_code="AI_RATE_LIMITED",
                    error_message=str(error),
                    retry_after=retry_after,
                    suggestions=["Wait before making another request"],
                ).model_dump(),
            ).model_dump(),
        )
    elif isinstance(error, AITimeoutError):
        return JSONResponse(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            content=ResponseSchema(
                status="error",
                message="AI request timed out",
                data=AIErrorResponse(
                    error_code="AI_TIMEOUT",
                    error_message=str(error),
                    suggestions=["Try again with a simpler request"],
                ).model_dump(),
            ).model_dump(),
        )
    elif isinstance(error, AIServiceUnavailableError):
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=ResponseSchema(
                status="error",
                message="AI service is temporarily unavailable",
                data=AIErrorResponse(
                    error_code="AI_SERVICE_UNAVAILABLE",
                    error_message=str(error),
                    suggestions=["Try again later"],
                ).model_dump(),
            ).model_dump(),
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ResponseSchema(
                status="error",
                message="AI service encountered an error",
                data=AIErrorResponse(
                    error_code="AI_SERVICE_ERROR",
                    error_message=str(error),
                    suggestions=["Try again later", "Contact support"],
                ).model_dump(),
            ).model_dump(),
        )
