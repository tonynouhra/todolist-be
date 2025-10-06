"""Notification service for task reminders."""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.email_service import email_service
from models.todo import Todo
from models.user import User
from models.user_settings import UserSettings


logger = logging.getLogger(__name__)


class NotificationService:
    """Service for handling task notifications."""

    def __init__(self, db: AsyncSession):
        """Initialize notification service.

        Args:
            db: Async database session
        """
        self.db = db
        self.email_service = email_service

    async def send_daily_reminders(self) -> dict[str, Any]:
        """Send daily reminders to all users with email notifications enabled.

        Returns:
            Dictionary with summary of notifications sent
        """
        logger.info("🔔 Starting daily reminder job...")

        # Get all users with email notifications enabled
        users = await self._get_users_with_email_notifications()

        stats = {
            "total_users": len(users),
            "emails_sent": 0,
            "emails_failed": 0,
            "users_with_tasks": 0,
        }

        for user in users:
            try:
                # Get tasks for this user
                expiring_tasks = await self._get_expiring_tasks(user.id)
                pending_tasks = await self._get_pending_tasks(user.id)

                # Skip if no tasks to report
                if not expiring_tasks and not pending_tasks:
                    logger.debug(f"No tasks to report for user {user.email}")
                    continue

                stats["users_with_tasks"] += 1

                # Format tasks for email
                expiring_data = [self._format_task(task) for task in expiring_tasks]
                pending_data = [self._format_task(task) for task in pending_tasks]

                # Send email
                username = user.username or user.email.split("@")[0]
                success = self.email_service.send_task_reminder(
                    to_email=user.email,
                    username=username,
                    expiring_tasks=expiring_data,
                    pending_tasks=pending_data,
                )

                if success:
                    stats["emails_sent"] += 1
                    logger.info(f"✅ Sent reminder to {user.email}")
                else:
                    stats["emails_failed"] += 1
                    logger.error(f"❌ Failed to send reminder to {user.email}")

            except Exception as e:
                stats["emails_failed"] += 1
                logger.error(f"❌ Error processing user {user.email}: {str(e)}")

        logger.info(
            f"📊 Daily reminders complete: {stats['emails_sent']} sent, "
            f"{stats['emails_failed']} failed, "
            f"{stats['users_with_tasks']} users with tasks"
        )

        return stats

    async def _get_users_with_email_notifications(self) -> list[User]:
        """Get all active users with email notifications enabled.

        Returns:
            List of User objects
        """
        query = (
            select(User)
            .join(UserSettings, User.id == UserSettings.user_id, isouter=True)
            .where(
                and_(
                    User.is_active == True,  # noqa: E712
                    or_(
                        # If settings exist, check if notifications are enabled
                        and_(
                            UserSettings.id.isnot(None),
                            UserSettings.notifications_enabled == True,  # noqa: E712
                            UserSettings.email_notifications == True,  # noqa: E712
                        ),
                        # If no settings exist, assume notifications are enabled (default)
                        UserSettings.id.is_(None),
                    ),
                )
            )
        )

        result = await self.db.execute(query)
        users = result.scalars().all()

        logger.info(f"Found {len(users)} users with email notifications enabled")
        return list(users)

    async def _get_expiring_tasks(self, user_id: Any, days_ahead: int = 3) -> list[Todo]:
        """Get tasks expiring within the specified number of days.

        Args:
            user_id: User ID
            days_ahead: Number of days to look ahead (default 3)

        Returns:
            List of Todo objects
        """
        now = datetime.now(UTC)
        future = now + timedelta(days=days_ahead)

        query = (
            select(Todo)
            .where(
                and_(
                    Todo.user_id == user_id,
                    Todo.status.in_(["todo", "in_progress"]),
                    Todo.due_date.isnot(None),
                    Todo.due_date >= now,
                    Todo.due_date <= future,
                )
            )
            .order_by(Todo.due_date.asc())
        )

        result = await self.db.execute(query)
        tasks = result.scalars().all()

        logger.debug(f"Found {len(tasks)} expiring tasks for user {user_id}")
        return list(tasks)

    async def _get_pending_tasks(self, user_id: Any, limit: int = 20) -> list[Todo]:
        """Get pending tasks for a user.

        Args:
            user_id: User ID
            limit: Maximum number of tasks to return

        Returns:
            List of Todo objects
        """
        query = (
            select(Todo)
            .where(
                and_(
                    Todo.user_id == user_id,
                    Todo.status == "todo",
                )
            )
            .order_by(
                Todo.priority.desc(),  # High priority first
                Todo.created_at.asc(),  # Older tasks first
            )
            .limit(limit)
        )

        result = await self.db.execute(query)
        tasks = result.scalars().all()

        logger.debug(f"Found {len(tasks)} pending tasks for user {user_id}")
        return list(tasks)

    def _format_task(self, task: Todo) -> dict[str, Any]:
        """Format a task for email display.

        Args:
            task: Todo object

        Returns:
            Dictionary with task data
        """
        return {
            "id": str(task.id),
            "title": task.title,
            "description": task.description,
            "priority": task.priority,
            "status": task.status,
            "due_date": task.due_date.strftime("%B %d, %Y at %I:%M %p") if task.due_date else None,
        }

    async def send_test_reminder(self, user_email: str) -> bool:
        """Send a test reminder email to a specific user.

        Args:
            user_email: Email address of the user

        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            # Get user
            query = select(User).where(User.email == user_email)
            result = await self.db.execute(query)
            user = result.scalar_one_or_none()

            if not user:
                logger.error(f"User not found: {user_email}")
                return False

            # Get tasks
            expiring_tasks = await self._get_expiring_tasks(user.id)
            pending_tasks = await self._get_pending_tasks(user.id)

            # Format tasks
            expiring_data = [self._format_task(task) for task in expiring_tasks]
            pending_data = [self._format_task(task) for task in pending_tasks]

            # Send email
            username = user.username or user.email.split("@")[0]
            success = self.email_service.send_task_reminder(
                to_email=user.email,
                username=username,
                expiring_tasks=expiring_data,
                pending_tasks=pending_data,
            )

            if success:
                logger.info(f"✅ Test reminder sent to {user_email}")
            else:
                logger.error(f"❌ Failed to send test reminder to {user_email}")

            return success

        except Exception as e:
            logger.error(f"❌ Error sending test reminder: {str(e)}")
            return False
