# ruff: noqa: SIM117
"""
Unit tests for SettingsService.

This module contains comprehensive unit tests for the SettingsService class,
testing all business logic methods with various scenarios and edge cases.
"""

from unittest.mock import patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.domains.settings.service import SettingsService


class TestSettingsService:
    """Test cases for SettingsService."""

    @pytest.mark.asyncio
    async def test_get_user_settings_existing(self, test_db, test_user, test_user_settings):
        """Test getting existing user settings."""
        service = SettingsService(test_db)

        result = await service.get_user_settings(test_user.id)

        assert result is not None
        assert result.id == test_user_settings.id
        assert result.user_id == test_user.id
        assert result.theme == test_user_settings.theme
        assert result.language == test_user_settings.language

    @pytest.mark.asyncio
    async def test_get_user_settings_creates_defaults(self, test_db, test_user):
        """Test that get_user_settings creates default settings if they don't exist."""
        service = SettingsService(test_db)

        # Ensure no settings exist
        result = await service.get_user_settings(test_user.id)

        assert result is not None
        assert result.user_id == test_user.id
        assert result.theme == "system"
        assert result.language == "en"
        assert result.timezone == "UTC"
        assert result.notifications_enabled is True
        assert result.email_notifications is True
        assert result.push_notifications is True

    @pytest.mark.asyncio
    async def test_create_default_settings_success(self, test_db, test_user):
        """Test successful creation of default settings."""
        service = SettingsService(test_db)

        result = await service.create_default_settings(test_user.id)

        assert result is not None
        assert result.user_id == test_user.id
        assert result.theme == "system"
        assert result.language == "en"
        assert result.timezone == "UTC"
        assert result.notifications_enabled is True
        assert result.email_notifications is True
        assert result.push_notifications is True
        assert result.id is not None

    @pytest.mark.asyncio
    async def test_create_default_settings_database_error(self, test_db, test_user):
        """Test create_default_settings with database error."""
        service = SettingsService(test_db)

        with patch.object(test_db, "commit", side_effect=SQLAlchemyError("Database error")):
            with patch.object(test_db, "rollback") as mock_rollback:
                with pytest.raises(SQLAlchemyError):
                    await service.create_default_settings(test_user.id)
                mock_rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_settings_theme(self, test_db, test_user, test_user_settings):
        """Test updating only theme setting."""
        service = SettingsService(test_db)
        original_language = test_user_settings.language

        result = await service.update_user_settings(user_id=test_user.id, theme="dark")

        assert result is not None
        assert result.theme == "dark"
        assert result.language == original_language  # Should remain unchanged

    @pytest.mark.asyncio
    async def test_update_user_settings_language(self, test_db, test_user, test_user_settings):
        """Test updating only language setting."""
        service = SettingsService(test_db)
        original_theme = test_user_settings.theme

        result = await service.update_user_settings(user_id=test_user.id, language="es")

        assert result is not None
        assert result.language == "es"
        assert result.theme == original_theme  # Should remain unchanged

    @pytest.mark.asyncio
    async def test_update_user_settings_timezone(self, test_db, test_user, test_user_settings):
        """Test updating timezone setting."""
        service = SettingsService(test_db)

        result = await service.update_user_settings(user_id=test_user.id, timezone="America/New_York")

        assert result is not None
        assert result.timezone == "America/New_York"

    @pytest.mark.asyncio
    async def test_update_user_settings_notifications(self, test_db, test_user, test_user_settings):
        """Test updating notification settings."""
        service = SettingsService(test_db)

        result = await service.update_user_settings(
            user_id=test_user.id,
            notifications_enabled=False,
            email_notifications=False,
            push_notifications=False,
        )

        assert result is not None
        assert result.notifications_enabled is False
        assert result.email_notifications is False
        assert result.push_notifications is False

    @pytest.mark.asyncio
    async def test_update_user_settings_multiple_fields(self, test_db, test_user, test_user_settings):
        """Test updating multiple settings at once."""
        service = SettingsService(test_db)

        result = await service.update_user_settings(
            user_id=test_user.id,
            theme="light",
            language="fr",
            timezone="Europe/Paris",
            notifications_enabled=False,
        )

        assert result is not None
        assert result.theme == "light"
        assert result.language == "fr"
        assert result.timezone == "Europe/Paris"
        assert result.notifications_enabled is False

    @pytest.mark.asyncio
    async def test_update_user_settings_creates_if_not_exists(self, test_db, test_user):
        """Test that update creates settings if they don't exist."""
        service = SettingsService(test_db)

        result = await service.update_user_settings(user_id=test_user.id, theme="dark", language="es")

        assert result is not None
        assert result.user_id == test_user.id
        assert result.theme == "dark"
        assert result.language == "es"

    @pytest.mark.asyncio
    async def test_update_user_settings_database_error(self, test_db, test_user, test_user_settings):
        """Test update_user_settings with database error."""
        service = SettingsService(test_db)

        with patch.object(test_db, "commit", side_effect=SQLAlchemyError("Database error")):
            with patch.object(test_db, "rollback") as mock_rollback:
                with pytest.raises(SQLAlchemyError):
                    await service.update_user_settings(user_id=test_user.id, theme="dark")
                mock_rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset_user_settings_success(self, test_db, test_user, test_user_settings):
        """Test successful settings reset to defaults."""
        service = SettingsService(test_db)

        # First modify settings
        await service.update_user_settings(
            user_id=test_user.id,
            theme="dark",
            language="es",
            timezone="Europe/Madrid",
            notifications_enabled=False,
        )

        # Then reset
        result = await service.reset_user_settings(test_user.id)

        assert result is not None
        assert result.theme == "system"
        assert result.language == "en"
        assert result.timezone == "UTC"
        assert result.notifications_enabled is True
        assert result.email_notifications is True
        assert result.push_notifications is True

    @pytest.mark.asyncio
    async def test_reset_user_settings_creates_if_not_exists(self, test_db, test_user):
        """Test that reset creates settings if they don't exist."""
        service = SettingsService(test_db)

        result = await service.reset_user_settings(test_user.id)

        assert result is not None
        assert result.user_id == test_user.id
        assert result.theme == "system"
        assert result.language == "en"

    @pytest.mark.asyncio
    async def test_delete_user_settings_success(self, test_db, test_user, test_user_settings):
        """Test successful deletion of user settings."""
        service = SettingsService(test_db)

        success = await service.delete_user_settings(test_user.id)

        assert success is True

        # Verify settings are deleted
        settings = await service.get_user_settings(test_user.id)
        # Should create new default settings
        assert settings.id != test_user_settings.id

    @pytest.mark.asyncio
    async def test_delete_user_settings_nonexistent(self, test_db, test_user):
        """Test deleting non-existent settings."""
        service = SettingsService(test_db)

        success = await service.delete_user_settings(test_user.id)

        assert success is False

    @pytest.mark.asyncio
    async def test_delete_user_settings_database_error(self, test_db, test_user, test_user_settings):
        """Test delete_user_settings with database error."""
        service = SettingsService(test_db)

        with patch.object(test_db, "commit", side_effect=SQLAlchemyError("Database error")):
            with patch.object(test_db, "rollback") as mock_rollback:
                with pytest.raises(SQLAlchemyError):
                    await service.delete_user_settings(test_user.id)
                mock_rollback.assert_called_once()
