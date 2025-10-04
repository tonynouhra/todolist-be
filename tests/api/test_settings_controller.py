"""
API tests for Settings controller.

This module contains comprehensive API endpoint tests for the settings
controller, testing all endpoints with various scenarios and edge cases.
"""

from unittest.mock import patch

import pytest
from fastapi import status
from httpx import AsyncClient


class TestSettingsController:
    """Test cases for Settings API endpoints."""

    @pytest.mark.asyncio
    async def test_get_settings_success(
        self, authenticated_client: AsyncClient, test_user, test_user_settings
    ):
        """Test successful retrieval of user settings."""
        response = await authenticated_client.get("/api/settings")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["user_id"] == str(test_user.id)
        assert data["theme"] == test_user_settings.theme
        assert data["language"] == test_user_settings.language
        assert data["timezone"] == test_user_settings.timezone

    @pytest.mark.asyncio
    async def test_get_settings_creates_defaults(self, authenticated_client: AsyncClient, test_user):
        """Test that get_settings creates defaults if they don't exist."""
        response = await authenticated_client.get("/api/settings")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["user_id"] == str(test_user.id)
        assert data["theme"] == "system"
        assert data["language"] == "en"
        assert data["timezone"] == "UTC"
        assert data["notifications_enabled"] is True
        assert data["email_notifications"] is True
        assert data["push_notifications"] is True

    @pytest.mark.asyncio
    async def test_get_settings_unauthorized(self, client: AsyncClient):
        """Test getting settings without authentication."""
        response = await client.get("/api/settings")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_get_settings_service_error(
        self, authenticated_client: AsyncClient, test_user, test_user_settings
    ):
        """Test get_settings with service error."""
        with patch(
            "app.domains.settings.service.SettingsService.get_user_settings",
            side_effect=Exception("Service error"),
        ):
            response = await authenticated_client.get("/api/settings")

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()
            assert "Failed to retrieve settings" in data["message"]

    @pytest.mark.asyncio
    async def test_update_settings_theme(
        self, authenticated_client: AsyncClient, test_user, test_user_settings
    ):
        """Test updating theme setting."""
        update_data = {"theme": "dark"}

        response = await authenticated_client.put("/api/settings", json=update_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["theme"] == "dark"
        assert data["user_id"] == str(test_user.id)

    @pytest.mark.asyncio
    async def test_update_settings_language(
        self, authenticated_client: AsyncClient, test_user, test_user_settings
    ):
        """Test updating language setting."""
        update_data = {"language": "es"}

        response = await authenticated_client.put("/api/settings", json=update_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["language"] == "es"

    @pytest.mark.asyncio
    async def test_update_settings_timezone(
        self, authenticated_client: AsyncClient, test_user, test_user_settings
    ):
        """Test updating timezone setting."""
        update_data = {"timezone": "America/New_York"}

        response = await authenticated_client.put("/api/settings", json=update_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["timezone"] == "America/New_York"

    @pytest.mark.asyncio
    async def test_update_settings_notifications(
        self, authenticated_client: AsyncClient, test_user, test_user_settings
    ):
        """Test updating notification settings."""
        update_data = {
            "notifications_enabled": False,
            "email_notifications": False,
            "push_notifications": False,
        }

        response = await authenticated_client.put("/api/settings", json=update_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["notifications_enabled"] is False
        assert data["email_notifications"] is False
        assert data["push_notifications"] is False

    @pytest.mark.asyncio
    async def test_update_settings_multiple_fields(
        self, authenticated_client: AsyncClient, test_user, test_user_settings
    ):
        """Test updating multiple settings at once."""
        update_data = {
            "theme": "light",
            "language": "fr",
            "timezone": "Europe/Paris",
            "notifications_enabled": False,
        }

        response = await authenticated_client.put("/api/settings", json=update_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["theme"] == "light"
        assert data["language"] == "fr"
        assert data["timezone"] == "Europe/Paris"
        assert data["notifications_enabled"] is False

    @pytest.mark.asyncio
    async def test_update_settings_partial(
        self, authenticated_client: AsyncClient, test_user, test_user_settings
    ):
        """Test partial update of settings."""
        original_language = test_user_settings.language
        update_data = {"theme": "dark"}  # Only update theme

        response = await authenticated_client.put("/api/settings", json=update_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["theme"] == "dark"
        assert data["language"] == original_language  # Should remain unchanged

    @pytest.mark.asyncio
    async def test_update_settings_invalid_theme(self, authenticated_client: AsyncClient):
        """Test updating with invalid theme value."""
        update_data = {"theme": "invalid_theme"}

        response = await authenticated_client.put("/api/settings", json=update_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_update_settings_invalid_language(self, authenticated_client: AsyncClient):
        """Test updating with invalid language value."""
        update_data = {"language": "123!@#"}  # Invalid characters

        response = await authenticated_client.put("/api/settings", json=update_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_update_settings_empty_language(self, authenticated_client: AsyncClient):
        """Test updating with empty language value."""
        update_data = {"language": ""}

        response = await authenticated_client.put("/api/settings", json=update_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_update_settings_unauthorized(self, client: AsyncClient):
        """Test updating settings without authentication."""
        update_data = {"theme": "dark"}

        response = await client.put("/api/settings", json=update_data)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_update_settings_service_error(
        self, authenticated_client: AsyncClient, test_user, test_user_settings
    ):
        """Test update_settings with service error."""
        update_data = {"theme": "dark"}

        with patch(
            "app.domains.settings.service.SettingsService.update_user_settings",
            side_effect=Exception("Service error"),
        ):
            response = await authenticated_client.put("/api/settings", json=update_data)

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()
            assert "Failed to update settings" in data["message"]

    @pytest.mark.asyncio
    async def test_reset_settings_success(
        self, authenticated_client: AsyncClient, test_user, test_user_settings
    ):
        """Test successful reset of settings to defaults."""
        # First update settings to non-default values
        await authenticated_client.put(
            "/api/settings",
            json={
                "theme": "dark",
                "language": "es",
                "timezone": "Europe/Madrid",
                "notifications_enabled": False,
            },
        )

        # Then reset
        response = await authenticated_client.post("/api/settings/reset")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["theme"] == "system"
        assert data["language"] == "en"
        assert data["timezone"] == "UTC"
        assert data["notifications_enabled"] is True
        assert data["email_notifications"] is True
        assert data["push_notifications"] is True

    @pytest.mark.asyncio
    async def test_reset_settings_creates_if_not_exists(
        self, authenticated_client: AsyncClient, test_user
    ):
        """Test that reset creates settings if they don't exist."""
        response = await authenticated_client.post("/api/settings/reset")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["user_id"] == str(test_user.id)
        assert data["theme"] == "system"
        assert data["language"] == "en"

    @pytest.mark.asyncio
    async def test_reset_settings_unauthorized(self, client: AsyncClient):
        """Test resetting settings without authentication."""
        response = await client.post("/api/settings/reset")

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_reset_settings_service_error(
        self, authenticated_client: AsyncClient, test_user, test_user_settings
    ):
        """Test reset_settings with service error."""
        with patch(
            "app.domains.settings.service.SettingsService.reset_user_settings",
            side_effect=Exception("Service error"),
        ):
            response = await authenticated_client.post("/api/settings/reset")

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()
            assert "Failed to reset settings" in data["message"]

    @pytest.mark.asyncio
    async def test_settings_endpoints_include_request_id(
        self, authenticated_client: AsyncClient, test_user, test_user_settings
    ):
        """Test that settings endpoints include request ID in response."""
        response = await authenticated_client.get("/api/settings")

        assert "x-request-id" in response.headers
        assert response.headers["x-request-id"] is not None

    @pytest.mark.asyncio
    async def test_update_settings_all_theme_options(
        self, authenticated_client: AsyncClient, test_user, test_user_settings
    ):
        """Test updating settings with all valid theme options."""
        themes = ["light", "dark", "system"]

        for theme in themes:
            response = await authenticated_client.put("/api/settings", json={"theme": theme})

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["theme"] == theme
