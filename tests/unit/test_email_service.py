"""Unit tests for Email Service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiosmtplib import SMTPException

from app.services.email_service import EmailService
from app.schemas.user import UserResponse


class TestEmailService:
    """Test cases for EmailService."""

    @pytest.fixture
    def email_service(self):
        """Create email service instance."""
        return EmailService()

    @pytest.fixture
    def mock_smtp_settings(self):
        """Mock SMTP settings."""
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.smtp_host = "smtp.test.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_user = "test@test.com"
            mock_settings.smtp_password = "password"
            mock_settings.email_from = "noreply@test.com"
            mock_settings.app_name = "Test App"
            yield mock_settings

    @pytest.fixture
    def test_user_data(self):
        """Test user data."""
        return {
            "email": "user@test.com",
            "username": "testuser",
            "id": "test-user-id"
        }

    @pytest.mark.asyncio
    async def test_send_welcome_email_success(
        self, email_service, mock_smtp_settings, test_user_data
    ):
        """Test sending welcome email successfully."""
        with patch("app.services.email_service.aiosmtplib.SMTP") as mock_smtp:
            mock_instance = AsyncMock()
            mock_smtp.return_value.__aenter__.return_value = mock_instance

            result = await email_service.send_welcome_email(
                test_user_data["email"],
                test_user_data["username"]
            )

            assert result is True
            mock_instance.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_welcome_email_no_smtp_config(
        self, email_service, test_user_data
    ):
        """Test sending welcome email without SMTP configuration."""
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.smtp_host = None

            result = await email_service.send_welcome_email(
                test_user_data["email"],
                test_user_data["username"]
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_send_welcome_email_smtp_error(
        self, email_service, mock_smtp_settings, test_user_data
    ):
        """Test sending welcome email with SMTP error."""
        with patch("app.services.email_service.aiosmtplib.SMTP") as mock_smtp:
            mock_instance = AsyncMock()
            mock_instance.send_message.side_effect = SMTPException("SMTP Error")
            mock_smtp.return_value.__aenter__.return_value = mock_instance

            result = await email_service.send_welcome_email(
                test_user_data["email"],
                test_user_data["username"]
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_send_todo_reminder_email_success(
        self, email_service, mock_smtp_settings, test_user_data
    ):
        """Test sending todo reminder email successfully."""
        with patch("app.services.email_service.aiosmtplib.SMTP") as mock_smtp:
            mock_instance = AsyncMock()
            mock_smtp.return_value.__aenter__.return_value = mock_instance

            todo_data = {
                "title": "Test Todo",
                "description": "Test Description",
                "due_date": "2024-12-31"
            }

            result = await email_service.send_todo_reminder_email(
                test_user_data["email"],
                todo_data
            )

            assert result is True
            mock_instance.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_password_reset_email_success(
        self, email_service, mock_smtp_settings, test_user_data
    ):
        """Test sending password reset email successfully."""
        with patch("app.services.email_service.aiosmtplib.SMTP") as mock_smtp:
            mock_instance = AsyncMock()
            mock_smtp.return_value.__aenter__.return_value = mock_instance

            result = await email_service.send_password_reset_email(
                test_user_data["email"],
                "reset-token-123"
            )

            assert result is True
            mock_instance.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_project_shared_email_success(
        self, email_service, mock_smtp_settings, test_user_data
    ):
        """Test sending project shared email successfully."""
        with patch("app.services.email_service.aiosmtplib.SMTP") as mock_smtp:
            mock_instance = AsyncMock()
            mock_smtp.return_value.__aenter__.return_value = mock_instance

            project_data = {
                "name": "Test Project",
                "shared_by": "John Doe"
            }

            result = await email_service.send_project_shared_email(
                test_user_data["email"],
                project_data
            )

            assert result is True
            mock_instance.send_message.assert_called_once()

    def test_create_message(self, email_service, mock_smtp_settings):
        """Test creating email message."""
        message = email_service._create_message(
            to_email="user@test.com",
            subject="Test Subject",
            body="Test Body"
        )

        assert message["To"] == "user@test.com"
        assert message["Subject"] == "Test Subject"
        assert "Test Body" in message.get_content()

    def test_is_configured_true(self, email_service, mock_smtp_settings):
        """Test email service is configured."""
        assert email_service._is_configured() is True

    def test_is_configured_false(self, email_service):
        """Test email service is not configured."""
        with patch("app.core.config.settings") as mock_settings:
            mock_settings.smtp_host = None

            assert email_service._is_configured() is False

    @pytest.mark.asyncio
    async def test_send_email_generic_success(
        self, email_service, mock_smtp_settings
    ):
        """Test generic email sending."""
        with patch("app.services.email_service.aiosmtplib.SMTP") as mock_smtp:
            mock_instance = AsyncMock()
            mock_smtp.return_value.__aenter__.return_value = mock_instance

            result = await email_service._send_email(
                to_email="user@test.com",
                subject="Test",
                body="Test Body"
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_send_batch_emails(self, email_service, mock_smtp_settings):
        """Test sending batch emails."""
        with patch("app.services.email_service.aiosmtplib.SMTP") as mock_smtp:
            mock_instance = AsyncMock()
            mock_smtp.return_value.__aenter__.return_value = mock_instance

            emails = [
                {"to": "user1@test.com", "subject": "Test 1", "body": "Body 1"},
                {"to": "user2@test.com", "subject": "Test 2", "body": "Body 2"},
            ]

            results = await email_service.send_batch_emails(emails)

            assert len(results) == 2
            assert all(results)