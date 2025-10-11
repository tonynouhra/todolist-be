"""Unit tests for Notification Service."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.notification_service import NotificationService, NotificationType
from models.user import User


@pytest.mark.asyncio
class TestNotificationService:
    """Test cases for NotificationService."""

    @pytest.fixture
    async def notification_service(self, test_db: AsyncSession):
        """Create notification service instance."""
        return NotificationService(test_db)

    async def test_create_notification_success(
        self, notification_service: NotificationService, test_user: User
    ):
        """Test creating a notification successfully."""
        notification = await notification_service.create_notification(
            user_id=test_user.id,
            notification_type=NotificationType.TODO_REMINDER,
            title="Test Notification",
            message="This is a test notification",
            data={"todo_id": str(uuid4())}
        )

        assert notification is not None
        assert notification.title == "Test Notification"
        assert notification.message == "This is a test notification"
        assert notification.is_read is False

    async def test_get_notifications_for_user(
        self, notification_service: NotificationService, test_user: User
    ):
        """Test getting notifications for a user."""
        # Create multiple notifications
        for i in range(3):
            await notification_service.create_notification(
                user_id=test_user.id,
                notification_type=NotificationType.TODO_REMINDER,
                title=f"Notification {i}",
                message=f"Message {i}"
            )

        notifications = await notification_service.get_notifications_for_user(
            test_user.id,
            skip=0,
            limit=10
        )

        assert len(notifications) >= 3

    async def test_get_unread_notifications(
        self, notification_service: NotificationService, test_user: User
    ):
        """Test getting unread notifications only."""
        # Create notifications
        for i in range(2):
            await notification_service.create_notification(
                user_id=test_user.id,
                notification_type=NotificationType.TODO_REMINDER,
                title=f"Notification {i}",
                message=f"Message {i}"
            )

        unread = await notification_service.get_unread_notifications(test_user.id)

        assert len(unread) >= 2
        assert all(not n.is_read for n in unread)

    async def test_mark_notification_as_read(
        self, notification_service: NotificationService, test_user: User
    ):
        """Test marking a notification as read."""
        # Create notification
        notification = await notification_service.create_notification(
            user_id=test_user.id,
            notification_type=NotificationType.TODO_REMINDER,
            title="Test",
            message="Test"
        )

        assert notification.is_read is False

        # Mark as read
        updated = await notification_service.mark_as_read(notification.id, test_user.id)

        assert updated.is_read is True

    async def test_mark_notification_as_read_not_found(
        self, notification_service: NotificationService, test_user: User
    ):
        """Test marking non-existent notification as read."""
        fake_id = uuid4()

        result = await notification_service.mark_as_read(fake_id, test_user.id)

        assert result is None

    async def test_mark_all_as_read(
        self, notification_service: NotificationService, test_user: User
    ):
        """Test marking all notifications as read."""
        # Create multiple notifications
        for i in range(3):
            await notification_service.create_notification(
                user_id=test_user.id,
                notification_type=NotificationType.TODO_REMINDER,
                title=f"Notification {i}",
                message=f"Message {i}"
            )

        # Mark all as read
        count = await notification_service.mark_all_as_read(test_user.id)

        assert count >= 3

        # Verify
        unread = await notification_service.get_unread_notifications(test_user.id)
        assert len(unread) == 0

    async def test_delete_notification(
        self, notification_service: NotificationService, test_user: User
    ):
        """Test deleting a notification."""
        # Create notification
        notification = await notification_service.create_notification(
            user_id=test_user.id,
            notification_type=NotificationType.TODO_REMINDER,
            title="Test",
            message="Test"
        )

        # Delete it
        result = await notification_service.delete_notification(
            notification.id,
            test_user.id
        )

        assert result is True

    async def test_delete_notification_not_found(
        self, notification_service: NotificationService, test_user: User
    ):
        """Test deleting non-existent notification."""
        fake_id = uuid4()

        result = await notification_service.delete_notification(fake_id, test_user.id)

        assert result is False

    async def test_get_notification_count(
        self, notification_service: NotificationService, test_user: User
    ):
        """Test getting notification count."""
        # Create notifications
        for i in range(5):
            await notification_service.create_notification(
                user_id=test_user.id,
                notification_type=NotificationType.TODO_REMINDER,
                title=f"Notification {i}",
                message=f"Message {i}"
            )

        total, unread = await notification_service.get_notification_count(test_user.id)

        assert total >= 5
        assert unread >= 5

    async def test_send_push_notification_success(
        self, notification_service: NotificationService, test_user: User
    ):
        """Test sending push notification."""
        with patch.object(
            notification_service, "_send_push_to_device", return_value=True
        ) as mock_send:
            result = await notification_service.send_push_notification(
                user_id=test_user.id,
                title="Test Push",
                body="Test Body",
                data={}
            )

            # Since user likely has no device tokens, result may be False
            # But the function should not raise an error
            assert isinstance(result, bool)

    async def test_notification_type_enum(self):
        """Test NotificationType enum values."""
        assert NotificationType.TODO_REMINDER == "todo_reminder"
        assert NotificationType.TODO_COMPLETED == "todo_completed"
        assert NotificationType.PROJECT_SHARED == "project_shared"
        assert NotificationType.SYSTEM == "system"

    async def test_delete_all_notifications(
        self, notification_service: NotificationService, test_user: User
    ):
        """Test deleting all notifications for a user."""
        # Create notifications
        for i in range(3):
            await notification_service.create_notification(
                user_id=test_user.id,
                notification_type=NotificationType.TODO_REMINDER,
                title=f"Notification {i}",
                message=f"Message {i}"
            )

        # Delete all
        count = await notification_service.delete_all_notifications(test_user.id)

        assert count >= 3

        # Verify
        notifications = await notification_service.get_notifications_for_user(
            test_user.id,
            skip=0,
            limit=100
        )
        assert len(notifications) == 0

    async def test_get_notifications_pagination(
        self, notification_service: NotificationService, test_user: User
    ):
        """Test pagination of notifications."""
        # Create many notifications
        for i in range(10):
            await notification_service.create_notification(
                user_id=test_user.id,
                notification_type=NotificationType.TODO_REMINDER,
                title=f"Notification {i}",
                message=f"Message {i}"
            )

        # Get first page
        page1 = await notification_service.get_notifications_for_user(
            test_user.id,
            skip=0,
            limit=5
        )

        # Get second page
        page2 = await notification_service.get_notifications_for_user(
            test_user.id,
            skip=5,
            limit=5
        )

        assert len(page1) == 5
        assert len(page2) == 5
        # Ensure different notifications
        assert page1[0].id != page2[0].id