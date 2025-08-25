"""
Unit tests for Configuration module - Working Version.

This module contains unit tests for the configuration settings that work
with the actual implementation.
"""

import os
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from app.core.config import (
    ConfigValidator,
    EnvironmentEnum,
    LogFormatEnum,
    LogLevelEnum,
    Settings,
    get_config_summary,
    settings,
)


class TestSettings:
    """Test cases for Settings configuration."""

    def test_default_settings(self):
        """Test that settings can be created with reasonable defaults."""
        test_settings = Settings()

        assert test_settings.app_name == "AI Todo List API"
        assert test_settings.environment == EnvironmentEnum.development
        assert test_settings.version == "1.0.0"
        assert test_settings.algorithm == "HS256"
        assert test_settings.access_token_expire_minutes == 30
        assert test_settings.db_pool_size == 20
        assert test_settings.db_max_overflow == 0
        assert test_settings.gemini_model == "gemini-1.5-flash"
        assert test_settings.gemini_max_tokens == 1000
        assert test_settings.ai_request_timeout == 30

    def test_environment_validation(self):
        """Test environment validation with shortcuts."""
        # Test shortcuts that actually work in the implementation
        test_settings = Settings(environment="dev")
        assert test_settings.environment == EnvironmentEnum.development

        test_settings = Settings(environment="prod")
        assert test_settings.environment == EnvironmentEnum.production

    def test_computed_properties(self):
        """Test computed properties."""
        # Test development environment
        dev_settings = Settings(environment="development")
        assert dev_settings.is_development is True
        assert dev_settings.is_production is False
        assert dev_settings.is_testing is False

        # Test production environment
        prod_settings = Settings(environment="production")
        assert prod_settings.is_development is False
        assert prod_settings.is_production is True
        assert prod_settings.is_testing is False

    def test_database_url_sync_property(self):
        """Test database URL sync conversion."""
        test_settings = Settings(database_url="postgresql+asyncpg://user:pass@host:5432/db")
        assert test_settings.database_url_sync == "postgresql://user:pass@host:5432/db"

        # Test with None database URL
        test_settings = Settings(database_url=None)
        assert test_settings.database_url_sync == ""

    def test_has_ai_enabled_property(self):
        """Test AI enabled property."""
        test_settings = Settings(gemini_api_key=None)
        assert test_settings.has_ai_enabled is False

        test_settings = Settings(gemini_api_key="")
        assert test_settings.has_ai_enabled is False

        test_settings = Settings(gemini_api_key="test_key")
        assert test_settings.has_ai_enabled is True

    def test_file_storage_with_explicit_none(self):
        """Test file storage with explicitly disabled storage."""
        test_settings = Settings(
            aws_access_key_id=None,
            aws_secret_access_key=None,
            s3_bucket_name=None,
            cloudflare_access_key_id=None,
            cloudflare_secret_access_key=None,
            cloudflare_bucket_name=None,
        )
        assert test_settings.has_file_storage is False

    def test_file_storage_with_aws(self):
        """Test file storage with AWS configured."""
        test_settings = Settings(
            aws_access_key_id="key", aws_secret_access_key="secret", s3_bucket_name="bucket"
        )
        assert test_settings.has_file_storage is True
        assert test_settings.storage_type == "aws_s3"

    def test_file_storage_with_cloudflare(self):
        """Test file storage with Cloudflare configured."""
        test_settings = Settings(
            cloudflare_access_key_id="key",
            cloudflare_secret_access_key="secret",
            cloudflare_bucket_name="bucket",
        )
        assert test_settings.has_file_storage is True
        assert test_settings.storage_type == "cloudflare_r2"

    def test_file_size_validation(self):
        """Test file size validation."""
        # Valid file size
        test_settings = Settings(max_file_size=50 * 1024 * 1024)  # 50MB
        assert test_settings.max_file_size == 50 * 1024 * 1024

        # Invalid file size (too large)
        with pytest.raises(ValidationError) as exc_info:
            Settings(max_file_size=150 * 1024 * 1024)  # 150MB
        assert "Maximum file size cannot exceed 100MB" in str(exc_info.value)

    def test_max_todos_validation(self):
        """Test max todos validation."""
        # Valid max todos
        test_settings = Settings(max_todos_per_user=500)
        assert test_settings.max_todos_per_user == 500

        # Invalid max todos (too high)
        with pytest.raises(ValidationError) as exc_info:
            Settings(max_todos_per_user=15000)
        assert "cannot exceed 10,000" in str(exc_info.value)

    def test_environment_variables_loading(self):
        """Test loading configuration from environment variables."""
        with patch.dict(
            os.environ,
            {
                "APP_NAME": "Test App",
                "ENVIRONMENT": "production",
                "DATABASE_URL": "postgresql://test",
                "GEMINI_API_KEY": "test_key",
            },
        ):
            test_settings = Settings()
            assert test_settings.app_name == "Test App"
            assert test_settings.environment == EnvironmentEnum.production
            assert test_settings.database_url == "postgresql://test"
            assert test_settings.gemini_api_key == "test_key"


class TestConfigValidator:
    """Test cases for ConfigValidator."""

    def test_validate_required_settings_with_mock(self):
        """Test validation with properly mocked settings."""
        # Create a test settings object instead of patching properties
        test_settings = Settings(
            database_url="postgresql://test",
            clerk_secret_key="test_key",
            environment="development",  # Not production, so AI key not required
            gemini_api_key="test_ai_key",
        )

        # Patch the module-level settings object
        with patch("app.core.config.settings", test_settings):
            # Should not raise exception
            ConfigValidator.validate_required_settings()

    def test_get_feature_status_actual(self):
        """Test feature status with actual implementation."""
        status = ConfigValidator.get_feature_status()

        # These should always be present
        assert "ai_enabled" in status
        assert "file_storage" in status
        assert "storage_type" in status
        assert "email_enabled" in status
        assert "monitoring_enabled" in status
        assert "environment" in status

        # Values should be boolean or string
        assert isinstance(status["ai_enabled"], bool)
        assert isinstance(status["file_storage"], bool)
        assert isinstance(status["email_enabled"], bool)
        assert isinstance(status["monitoring_enabled"], bool)
        assert status["storage_type"] in ["none", "aws_s3", "cloudflare_r2"]


class TestEnums:
    """Test cases for configuration enums."""

    def test_environment_enum(self):
        """Test EnvironmentEnum values."""
        assert EnvironmentEnum.development == "development"
        assert EnvironmentEnum.testing == "testing"
        assert EnvironmentEnum.staging == "staging"
        assert EnvironmentEnum.production == "production"

    def test_log_level_enum(self):
        """Test LogLevelEnum values."""
        assert LogLevelEnum.DEBUG == "DEBUG"
        assert LogLevelEnum.INFO == "INFO"
        assert LogLevelEnum.WARNING == "WARNING"
        assert LogLevelEnum.ERROR == "ERROR"
        assert LogLevelEnum.CRITICAL == "CRITICAL"

    def test_log_format_enum(self):
        """Test LogFormatEnum values."""
        assert LogFormatEnum.simple == "simple"
        assert LogFormatEnum.json == "json"


def test_get_config_summary():
    """Test configuration summary function."""
    summary = get_config_summary()

    # Test that the summary has expected keys
    expected_keys = [
        "app_name",
        "version",
        "environment",
        "debug",
        "features",
        "database_configured",
        "auth_configured",
        "storage_type",
    ]

    for key in expected_keys:
        assert key in summary

    # Test basic types
    assert isinstance(summary["app_name"], str)
    assert isinstance(summary["version"], str)
    assert isinstance(summary["debug"], bool)
    assert isinstance(summary["features"], dict)
