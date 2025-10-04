"""User Settings Pydantic schemas for request/response validation."""

from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator

from .base import BaseModelSchema, BaseSchema


ThemeType = Literal["light", "dark", "system"]


class UserSettingsResponse(BaseModelSchema):
    """Schema for user settings response data."""

    user_id: UUID
    theme: ThemeType
    language: str
    timezone: str
    notifications_enabled: bool
    email_notifications: bool
    push_notifications: bool


class UserSettingsUpdate(BaseSchema):
    """Schema for updating user settings (all fields optional)."""

    theme: ThemeType | None = Field(None, description="UI theme preference")
    language: str | None = Field(None, max_length=10, description="Language code (e.g., 'en', 'es')")
    timezone: str | None = Field(None, max_length=50, description="Timezone (e.g., 'America/New_York')")
    notifications_enabled: bool | None = Field(None, description="Master notification toggle")
    email_notifications: bool | None = Field(None, description="Email notifications enabled")
    push_notifications: bool | None = Field(None, description="Push notifications enabled")

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str | None) -> str | None:
        """Validate language code format."""
        if v is not None and v:
            if not v.strip():
                raise ValueError("Language code cannot be empty")
            # Basic validation for language code format (2-5 chars, letters and hyphens)
            if not all(c.isalpha() or c == "-" for c in v):
                raise ValueError("Language code must contain only letters and hyphens")
        return v

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, v: str | None) -> str | None:
        """Validate timezone string."""
        if v is not None and v:
            if not v.strip():
                raise ValueError("Timezone cannot be empty")
        return v


class UserSettingsCreate(BaseSchema):
    """Schema for creating user settings with defaults."""

    theme: ThemeType = Field(default="system", description="UI theme preference")
    language: str = Field(default="en", max_length=10, description="Language code")
    timezone: str = Field(default="UTC", max_length=50, description="Timezone")
    notifications_enabled: bool = Field(default=True, description="Master notification toggle")
    email_notifications: bool = Field(default=True, description="Email notifications enabled")
    push_notifications: bool = Field(default=True, description="Push notifications enabled")
