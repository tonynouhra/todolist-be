"""Notification API controller."""

import logging

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, validate_token
from app.schemas.base import ResponseSchema
from app.tasks.notification_tasks import send_test_reminder_task
from models.user import User


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/notifications",
    tags=["notifications"],
    dependencies=[Depends(validate_token)],
)


@router.post("/test-reminder", response_model=ResponseSchema)
async def send_test_reminder(
    _request: Request,
    current_user: User = Depends(get_current_user),
    _db: AsyncSession = Depends(get_db),
):
    """Send a test reminder email to the current user.

    This endpoint triggers a test email notification to verify the
    email notification system is working correctly.
    """
    try:
        logger.info(f"Sending test reminder to {current_user.email}")

        # Queue the Celery task
        task = send_test_reminder_task.delay(current_user.email)

        return ResponseSchema(
            status="success",
            message=f"Test reminder email queued successfully. Check your inbox at {current_user.email}",
            data={
                "task_id": task.id,
                "email": current_user.email,
                "status": "queued",
            },
        )

    except Exception as e:
        logger.error(f"Failed to queue test reminder: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ResponseSchema(
                status="error",
                message="Failed to queue test reminder email",
                data={"error": str(e)},
            ).model_dump(),
        )


@router.get("/task-status/{task_id}", response_model=ResponseSchema)
async def get_task_status(
    task_id: str,
    _request: Request,
    _current_user: User = Depends(get_current_user),
):
    """Get the status of a background notification task.

    Args:
        task_id: The Celery task ID
    """
    try:
        from app.celery_app import celery_app

        # Get task result
        task_result = celery_app.AsyncResult(task_id)

        return ResponseSchema(
            status="success",
            message="Task status retrieved successfully",
            data={
                "task_id": task_id,
                "status": task_result.status,
                "result": task_result.result if task_result.ready() else None,
            },
        )

    except Exception as e:
        logger.error(f"Failed to get task status: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ResponseSchema(
                status="error",
                message="Failed to get task status",
                data={"error": str(e)},
            ).model_dump(),
        )
