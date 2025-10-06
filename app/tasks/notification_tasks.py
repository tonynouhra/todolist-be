"""Celery tasks for notifications."""

import asyncio
import logging
from typing import Any

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Import all models to ensure they're registered before creating session
import models  # noqa: F401

from app.celery_app import celery_app
from app.core.config import settings
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


def get_async_session() -> AsyncSession:
    """Create an async database session for Celery tasks.

    Returns:
        Async database session
    """
    engine = create_async_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )

    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    return async_session_maker()


@celery_app.task(name="app.tasks.notification_tasks.send_daily_reminders_task", bind=True)
def send_daily_reminders_task(self) -> dict[str, Any]:
    """Send daily task reminders to all users.

    This is the main scheduled task that runs daily via Celery Beat.

    Returns:
        Dictionary with task execution statistics
    """
    logger.info(f"🚀 Starting daily reminders task (Task ID: {self.request.id})")

    try:
        # Run the async function in a synchronous context
        result = asyncio.run(_send_daily_reminders_async())
        logger.info(f"✅ Daily reminders task completed successfully: {result}")
        return result

    except Exception as e:
        logger.error(f"❌ Daily reminders task failed: {str(e)}")
        # Retry the task with exponential backoff
        raise self.retry(exc=e, countdown=60 * 5, max_retries=3)


async def _send_daily_reminders_async() -> dict[str, Any]:
    """Async function to send daily reminders.

    Returns:
        Dictionary with execution statistics
    """
    session = get_async_session()

    try:
        async with session.begin():
            notification_service = NotificationService(session)
            stats = await notification_service.send_daily_reminders()
            return stats

    except Exception as e:
        await session.rollback()
        logger.error(f"Error in daily reminders: {str(e)}")
        raise

    finally:
        await session.close()


@celery_app.task(name="app.tasks.notification_tasks.send_test_reminder_task")
def send_test_reminder_task(user_email: str) -> dict[str, Any]:
    """Send a test reminder email to a specific user.

    Args:
        user_email: Email address of the user

    Returns:
        Dictionary with result
    """
    logger.info(f"📧 Sending test reminder to {user_email}")

    try:
        result = asyncio.run(_send_test_reminder_async(user_email))

        if result:
            logger.info(f"✅ Test reminder sent to {user_email}")
            return {"success": True, "email": user_email}
        else:
            logger.error(f"❌ Failed to send test reminder to {user_email}")
            return {"success": False, "email": user_email, "error": "Email send failed"}

    except Exception as e:
        logger.error(f"❌ Test reminder task failed: {str(e)}")
        return {"success": False, "email": user_email, "error": str(e)}


async def _send_test_reminder_async(user_email: str) -> bool:
    """Async function to send test reminder.

    Args:
        user_email: Email address of the user

    Returns:
        True if successful, False otherwise
    """
    session = get_async_session()

    try:
        async with session.begin():
            notification_service = NotificationService(session)
            success = await notification_service.send_test_reminder(user_email)
            return success

    except Exception as e:
        await session.rollback()
        logger.error(f"Error sending test reminder: {str(e)}")
        return False

    finally:
        await session.close()
