# app/domains/settings/service.py
"""Settings service for managing user preferences and configuration."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from models import UserSettings


class SettingsService:
    """Service for managing user settings and preferences."""

    def __init__(self, db: AsyncSession):
        """Initialize service with a database session."""
        self.db = db

    async def get_user_settings(self, user_id: UUID) -> UserSettings:
        """
        Get user settings, creating with defaults if they don't exist.

        Args:
            user_id: The user's unique identifier

        Returns:
            UserSettings: The user's settings object

        Raises:
            SQLAlchemyError: If database operation fails
        """
        result = await self.db.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        settings = result.scalar_one_or_none()

        if not settings:
            # Create default settings for user
            settings = await self.create_default_settings(user_id)

        return settings

    async def create_default_settings(self, user_id: UUID) -> UserSettings:
        """
        Create default settings for a user.

        Args:
            user_id: The user's unique identifier

        Returns:
            UserSettings: Newly created settings with defaults

        Raises:
            SQLAlchemyError: If database operation fails
        """
        settings = UserSettings(
            user_id=user_id,
            theme="system",
            language="en",
            timezone="UTC",
            notifications_enabled=True,
            email_notifications=True,
            push_notifications=True,
        )

        try:
            self.db.add(settings)
            await self.db.commit()
            await self.db.refresh(settings)
            return settings
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise e

    async def update_user_settings(
        self,
        user_id: UUID,
        theme: str | None = None,
        language: str | None = None,
        timezone: str | None = None,
        notifications_enabled: bool | None = None,
        email_notifications: bool | None = None,
        push_notifications: bool | None = None,
    ) -> UserSettings:
        """
        Update user settings with provided values.

        Args:
            user_id: The user's unique identifier
            theme: Theme preference (light, dark, system)
            language: Language code
            timezone: Timezone string
            notifications_enabled: Master notification toggle
            email_notifications: Email notifications enabled
            push_notifications: Push notifications enabled

        Returns:
            UserSettings: Updated settings object

        Raises:
            SQLAlchemyError: If database operation fails
        """
        # Get or create settings
        settings = await self.get_user_settings(user_id)

        try:
            # Update only provided fields
            if theme is not None:
                settings.theme = theme
            if language is not None:
                settings.language = language
            if timezone is not None:
                settings.timezone = timezone
            if notifications_enabled is not None:
                settings.notifications_enabled = notifications_enabled
            if email_notifications is not None:
                settings.email_notifications = email_notifications
            if push_notifications is not None:
                settings.push_notifications = push_notifications

            await self.db.commit()
            await self.db.refresh(settings)
            return settings
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise e

    async def reset_user_settings(self, user_id: UUID) -> UserSettings:
        """
        Reset user settings to defaults.

        Args:
            user_id: The user's unique identifier

        Returns:
            UserSettings: Settings reset to defaults

        Raises:
            SQLAlchemyError: If database operation fails
        """
        return await self.update_user_settings(
            user_id=user_id,
            theme="system",
            language="en",
            timezone="UTC",
            notifications_enabled=True,
            email_notifications=True,
            push_notifications=True,
        )

    async def delete_user_settings(self, user_id: UUID) -> bool:
        """
        Delete user settings.

        Args:
            user_id: The user's unique identifier

        Returns:
            bool: True if deleted, False if settings didn't exist

        Raises:
            SQLAlchemyError: If database operation fails
        """
        result = await self.db.execute(
            select(UserSettings).where(UserSettings.user_id == user_id)
        )
        settings = result.scalar_one_or_none()

        if not settings:
            return False

        try:
            await self.db.delete(settings)
            await self.db.commit()
            return True
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise e
