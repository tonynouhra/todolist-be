"""
Unit tests for Configuration module.

This module contains comprehensive unit tests for the configuration settings,
validators, and computed properties.
"""

import os
import tempfile
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
        """Test default configuration values."""
        test_settings = Settings()
        
        assert test_settings.app_name == "AI Todo List API"
        assert test_settings.environment == EnvironmentEnum.development
        assert test_settings.debug is False
        assert test_settings.version == "1.0.0"
        assert test_settings.algorithm == "HS256"
        assert test_settings.access_token_expire_minutes == 30
        assert test_settings.db_pool_size == 20
        assert test_settings.db_max_overflow == 0
        assert test_settings.gemini_model == "gemini-1.5-flash"
        assert test_settings.gemini_max_tokens == 1000
        assert test_settings.ai_request_timeout == 30

    def test_environment_validation(self):
        """Test environment validation with various inputs."""
        # Test direct enum values
        test_settings = Settings(environment="production")
        assert test_settings.environment == EnvironmentEnum.production
        
        # Test case insensitive
        test_settings = Settings(environment="DEVELOPMENT")
        assert test_settings.environment == EnvironmentEnum.development
        
        # Test shortcuts
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
        
        # Test testing environment
        test_settings = Settings(environment="testing")
        assert test_settings.is_development is False
        assert test_settings.is_production is False
        assert test_settings.is_testing is True

    def test_database_url_sync_property(self):
        """Test database URL sync conversion."""
        test_settings = Settings(database_url="postgresql+asyncpg://user:pass@host:5432/db")
        assert test_settings.database_url_sync == "postgresql://user:pass@host:5432/db"
        
        # Test with empty database URL
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

    def test_has_file_storage_property(self):
        """Test file storage enabled property."""
        # Test no storage configured
        test_settings = Settings()
        assert test_settings.has_file_storage is False
        
        # Test AWS S3 configured
        test_settings = Settings(
            aws_access_key_id="key",
            aws_secret_access_key="secret",
            s3_bucket_name="bucket"
        )
        assert test_settings.has_file_storage is True
        
        # Test Cloudflare R2 configured
        test_settings = Settings(
            cloudflare_access_key_id="key",
            cloudflare_secret_access_key="secret",
            cloudflare_bucket_name="bucket"
        )
        assert test_settings.has_file_storage is True

    def test_storage_type_property(self):
        """Test storage type property."""
        # Test no storage
        test_settings = Settings()
        assert test_settings.storage_type == "none"
        
        # Test AWS S3
        test_settings = Settings(
            aws_access_key_id="key",
            aws_secret_access_key="secret",
            s3_bucket_name="bucket"
        )
        assert test_settings.storage_type == "aws_s3"
        
        # Test Cloudflare R2 (takes precedence)
        test_settings = Settings(
            aws_access_key_id="key",
            aws_secret_access_key="secret",
            s3_bucket_name="bucket",
            cloudflare_access_key_id="cf_key",
            cloudflare_secret_access_key="cf_secret",
            cloudflare_bucket_name="cf_bucket"
        )
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
        
        # Invalid max todos (too high) - WRONG LIMIT
        with pytest.raises(ValidationError) as exc_info:
            Settings(max_todos_per_user=15000)  # Changed from 1500 to 15000
        assert "cannot exceed 10,000" in str(exc_info.value)  # Changed from 1000 to 10,000

    def test_environment_variables_loading(self):
        """Test loading configuration from environment variables."""
        with patch.dict(os.environ, {
            "APP_NAME": "Test App",
            "ENVIRONMENT": "production",
            "DEBUG": "true",
            "DATABASE_URL": "postgresql://test",
            "GEMINI_API_KEY": "test_key"
        }):
            test_settings = Settings()
            assert test_settings.app_name == "Test App"
            assert test_settings.environment == EnvironmentEnum.production
            assert test_settings.debug is True
            assert test_settings.database_url == "postgresql://test"
            assert test_settings.gemini_api_key == "test_key"

    def test_secret_key_generation(self):
        """Test secret key auto-generation."""
        test_settings1 = Settings()
        test_settings2 = Settings()
        
        # Should generate different keys each time
        assert test_settings1.secret_key != test_settings2.secret_key
        assert len(test_settings1.secret_key) > 0
        assert len(test_settings2.secret_key) > 0


class TestConfigValidator:
    """Test cases for ConfigValidator."""

    def test_validate_required_settings_success(self):
        """Test successful validation of required settings."""
        with patch.object(settings, 'database_url', 'postgresql://test'):
            with patch.object(settings, 'clerk_secret_key', 'test_key'):
                with patch.object(settings, 'is_production', False):
                    # Should not raise exception
                    ConfigValidator.validate_required_settings()

    def test_validate_required_settings_missing_database(self):
        """Test validation failure with missing database URL."""
        with patch.object(settings, 'database_url', None):
            with patch.object(settings, 'clerk_secret_key', 'test_key'):
                with pytest.raises(ValueError) as exc_info:
                    ConfigValidator.validate_required_settings()
                assert "DATABASE_URL is required" in str(exc_info.value)

    def test_validate_required_settings_missing_clerk(self):
        """Test validation failure with missing Clerk secret."""
        with patch.object(settings, 'database_url', 'postgresql://test'):
            with patch.object(settings, 'clerk_secret_key', None):
                with pytest.raises(ValueError) as exc_info:
                    ConfigValidator.validate_required_settings()
                assert "CLERK_SECRET_KEY is required" in str(exc_info.value)

    def test_validate_required_settings_production_missing_ai(self):
        """Test validation failure in production without AI key."""
        with patch.object(settings, 'database_url', 'postgresql://test'):
            with patch.object(settings, 'clerk_secret_key', 'test_key'):
                with patch.object(settings, 'is_production', True):
                    with patch.object(settings, 'gemini_api_key', None):
                        with pytest.raises(ValueError) as exc_info:
                            ConfigValidator.validate_required_settings()
                        assert "GEMINI_API_KEY is required in production" in str(exc_info.value)

    def test_get_feature_status(self):
        """Test feature status retrieval."""
        with patch.object(settings, 'has_ai_enabled', True):
            with patch.object(settings, 'has_file_storage', False):
                with patch.object(settings, 'storage_type', 'none'):
                    with patch.object(settings, 'smtp_host', None):
                        with patch.object(settings, 'smtp_user', None):
                            with patch.object(settings, 'sentry_dsn', None):
                                with patch.object(settings, 'environment', EnvironmentEnum.development):
                                    status = ConfigValidator.get_feature_status()
                                    
                                    assert status['ai_enabled'] is True
                                    assert status['file_storage'] is False
                                    assert status['storage_type'] == 'none'
                                    assert status['email_enabled'] is False
                                    assert status['monitoring_enabled'] is False
                                    assert status['environment'] == EnvironmentEnum.development


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
    with patch.object(settings, 'app_name', 'Test App'):
        with patch.object(settings, 'version', '2.0.0'):
            with patch.object(settings, 'environment', EnvironmentEnum.production):
                summary = get_config_summary()
                
                assert 'app_name' in summary
                assert 'version' in summary
                assert 'environment' in summary
                assert summary['app_name'] == 'Test App'
                assert summary['version'] == '2.0.0'
                assert summary['environment'] == EnvironmentEnum.production
