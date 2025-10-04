"""
User Settings model for storing user preferences and configuration.

This module defines the UserSettings model which manages user-specific
preferences including theme, language, timezone, and notification settings.
"""

from sqlalchemy import Boolean, Column, Enum, ForeignKey, String
from sqlalchemy.orm import relationship

from .base import UUID, BaseModel


class UserSettings(BaseModel):
    """
    Represents user settings and preferences.

    This class defines the structure of user settings, including theme
    preferences, language, timezone, and notification configurations.
    Each user has one settings record (one-to-one relationship).

    :ivar user_id: Foreign key reference to the user.
    :type user_id: UUID
    :ivar theme: UI theme preference (light, dark, system).
    :type theme: str
    :ivar language: Preferred language code (en, es, fr, etc.).
    :type language: str
    :ivar timezone: User's timezone (e.g., 'America/New_York').
    :type timezone: str
    :ivar notifications_enabled: Master switch for all notifications.
    :type notifications_enabled: bool
    :ivar email_notifications: Enable email notifications.
    :type email_notifications: bool
    :ivar push_notifications: Enable push notifications.
    :type push_notifications: bool
    """

    __tablename__ = "user_settings"

    # Foreign key to user
    user_id = Column(UUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Theme settings
    theme = Column(
        Enum("light", "dark", "system", name="theme_type"),
        default="system",
        nullable=False,
    )

    # Localization settings
    language = Column(String(10), default="en", nullable=False)
    timezone = Column(String(50), default="UTC", nullable=False)

    # Notification preferences
    notifications_enabled = Column(Boolean, default=True, nullable=False)
    email_notifications = Column(Boolean, default=True, nullable=False)
    push_notifications = Column(Boolean, default=True, nullable=False)

    # Relationship
    user = relationship("User", back_populates="settings")
