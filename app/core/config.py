# python
# app/core/config.py
"""Configuration settings for AI Todo List application.

Uses Pydantic BaseSettings for environment variable management.
"""
import secrets
from enum import Enum

from pydantic import AnyHttpUrl, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvironmentEnum(str, Enum):
    development = "development"
    testing = "testing"
    staging = "staging"
    production = "production"


class LogLevelEnum(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormatEnum(str, Enum):
    simple = "simple"
    json = "json"


class Settings(BaseSettings):
    # Pydantic v2 settings configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ===== Application Settings =====
    app_name: str = Field(default="AI Todo List API", description="Application name")
    environment: EnvironmentEnum = Field(
        default=EnvironmentEnum.development, description="Environment type"
    )
    debug: bool = Field(default=False, description="Debug mode")
    version: str = Field(default="1.0.0", description="Application version")

    # ===== Security Settings =====
    secret_key: str = Field(
        default_factory=lambda: secrets.token_urlsafe(32),
        description="Secret key for JWT encoding",
    )
    algorithm: str = Field(default="HS256", description="JWT algorithm")
    access_token_expire_minutes: int = Field(default=30, description="JWT token expiration time")

    # ===== Database Settings =====
    database_url: str | None = Field(default=None, description="Database connection URL")
    db_pool_size: int = Field(default=20, description="Database connection pool size")
    db_max_overflow: int = Field(default=0, description="Database max overflow connections")

    # Test database URL
    test_database_url: str | None = Field(default=None, description="Test database URL")

    # ===== Authentication (Clerk) =====
    clerk_secret_key: str | None = Field(default=None, description="Clerk secret key")
    clerk_api_url: AnyHttpUrl = Field(default="https://api.clerk.com", description="Clerk API URL")

    # ===== AI Service (Gemini) =====
    gemini_api_key: str | None = Field(default=None, description="Google Gemini API key")
    gemini_model: str = Field(default="gemini-1.5-flash", description="Gemini model to use")
    gemini_max_tokens: int = Field(default=1000, description="Maximum tokens for Gemini")
    ai_request_timeout: int = Field(default=30, description="AI request timeout in seconds")

    # ===== File Storage Settings =====
    aws_access_key_id: str | None = Field(default=None, description="AWS access key ID")
    aws_secret_access_key: str | None = Field(default=None, description="AWS secret access key")
    s3_bucket_name: str | None = Field(default=None, description="S3 bucket name")
    s3_region: str = Field(default="us-east-1", description="S3 region")
    s3_endpoint_url: str | None = Field(default=None, description="S3 endpoint URL")

    cloudflare_account_id: str | None = Field(default=None, description="CloudFlare account ID")
    cloudflare_access_key_id: str | None = Field(
        default=None, description="CloudFlare R2 access key"
    )
    cloudflare_secret_access_key: str | None = Field(
        default=None, description="CloudFlare R2 secret key"
    )
    cloudflare_bucket_name: str | None = Field(
        default=None, description="CloudFlare R2 bucket name"
    )

    # ===== Redis Configuration =====
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis connection URL")

    # ===== Application Limits =====
    max_file_size: int = Field(default=52428800, description="Maximum file size in bytes (50MB)")
    max_todos_per_user: int = Field(default=1000, description="Maximum todos per user")
    max_subtasks_depth: int = Field(default=5, description="Maximum subtask nesting depth")
    max_files_per_todo: int = Field(default=10, description="Maximum files per todo")
    file_upload_timeout: int = Field(default=60, description="File upload timeout in seconds")

    # ===== Rate Limiting =====
    rate_limit_requests: int = Field(default=100, description="Rate limit requests per period")
    rate_limit_period: int = Field(default=60, description="Rate limit period in seconds")

    # ===== CORS Settings =====
    allowed_origins: str = Field(
        default="http://localhost:3000,http://localhost:5173,http://localhost:8080,http://127.0.0.1:3000",
        description="Allowed CORS origins (comma-separated)",
    )

    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        if isinstance(self.allowed_origins, str):
            return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]
        return self.allowed_origins if isinstance(self.allowed_origins, list) else []

    # ===== Background Tasks (Celery) =====
    celery_broker_url: str = Field(
        default="redis://localhost:6379/1", description="Celery broker URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/2", description="Celery result backend"
    )

    # ===== Email Configuration =====
    smtp_host: str | None = Field(default=None, description="SMTP host")
    smtp_port: int = Field(default=587, description="SMTP port")
    smtp_user: str | None = Field(default=None, description="SMTP username")
    smtp_password: str | None = Field(default=None, description="SMTP password")
    email_from: str | None = Field(default=None, description="Email from address")

    # ===== Monitoring & Logging =====
    log_level: LogLevelEnum = Field(default=LogLevelEnum.INFO, description="Logging level")
    log_format: LogFormatEnum = Field(default=LogFormatEnum.json, description="Log format")
    sentry_dsn: str | None = Field(default=None, description="Sentry DSN for error tracking")

    # ===== WebSocket Configuration =====
    websocket_heartbeat_interval: int = Field(
        default=30, description="WebSocket heartbeat interval"
    )
    websocket_max_connections: int = Field(
        default=1000, description="Maximum WebSocket connections"
    )

    # ===== Server Settings =====
    host: str = Field(default="127.0.0.1", description="Host to bind the server")
    port: int = Field(default=8000, description="Port to bind the server")

    # ===== Development Settings =====
    reload: bool = Field(default=False, description="Auto-reload in development")
    docs_url: str = Field(default="/docs", description="API documentation URL")
    redoc_url: str = Field(default="/redoc", description="ReDoc documentation URL")

    # ===== Computed Properties =====
    @property
    def is_development(self) -> bool:
        return self.environment == EnvironmentEnum.development

    @property
    def is_production(self) -> bool:
        return self.environment == EnvironmentEnum.production

    @property
    def is_testing(self) -> bool:
        return self.environment == EnvironmentEnum.testing

    @property
    def database_url_sync(self) -> str:
        if not self.database_url:
            return ""
        return self.database_url.replace("postgresql+asyncpg://", "postgresql://")

    @property
    def has_ai_enabled(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def has_file_storage(self) -> bool:
        return bool(
            (self.aws_access_key_id and self.aws_secret_access_key and self.s3_bucket_name)
            or (
                self.cloudflare_access_key_id
                and self.cloudflare_secret_access_key
                and self.cloudflare_bucket_name
            )
        )

    @property
    def storage_type(self) -> str:
        if self.cloudflare_access_key_id:
            return "cloudflare_r2"
        if self.aws_access_key_id:
            return "aws_s3"
        return "none"

    # ===== Validation Methods =====
    @field_validator("environment", mode="before")
    @classmethod
    def validate_environment(cls, v):
        if v and isinstance(v, str):
            lv = v.lower()
            if lv in ["dev", "develop"]:
                return "development"
            if lv in ["prod"]:
                return "production"
        return v

    @field_validator("max_file_size")
    @classmethod
    def validate_file_size(cls, v):
        if v > 100 * 1024 * 1024:
            raise ValueError("Maximum file size cannot exceed 100MB")
        return v

    @field_validator("max_todos_per_user")
    @classmethod
    def validate_max_todos(cls, v):
        if v > 10000:
            raise ValueError("Maximum todos per user cannot exceed 10,000")
        return v

    @model_validator(mode="after")
    def set_computed_fields(self):
        if not self.test_database_url and self.database_url and "neondb" in self.database_url:
            self.test_database_url = self.database_url.replace("neondb", "neondb_test")
        return self


settings = Settings()


class ConfigValidator:
    @staticmethod
    def validate_required_settings():
        errors = []
        if not settings.database_url:
            errors.append("DATABASE_URL is required")
        if not settings.clerk_secret_key:
            errors.append("CLERK_SECRET_KEY is required")
        if settings.is_production and not settings.gemini_api_key:
            errors.append("GEMINI_API_KEY is required in production")
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")

    @staticmethod
    def get_feature_status() -> dict:
        return {
            "ai_enabled": settings.has_ai_enabled,
            "file_storage": settings.has_file_storage,
            "storage_type": settings.storage_type,
            "email_enabled": bool(settings.smtp_host and settings.smtp_user),
            "monitoring_enabled": bool(settings.sentry_dsn),
            "environment": settings.environment,
        }


def get_config_summary() -> dict:
    return {
        "app_name": settings.app_name,
        "version": settings.version,
        "environment": settings.environment,
        "debug": settings.debug,
        "features": ConfigValidator.get_feature_status(),
        "database_configured": bool(settings.database_url),
        "auth_configured": bool(settings.clerk_secret_key),
        "storage_type": settings.storage_type,
    }


__all__ = [
    "settings",
    "Settings",
    "ConfigValidator",
    "get_config_summary",
    "EnvironmentEnum",
    "LogLevelEnum",
    "LogFormatEnum",
]
