"""Base schemas for the application."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict
from uuid import UUID
from typing import Optional


class BaseSchema(BaseModel):
    """Base schema class with common configuration."""
    model_config = ConfigDict(from_attributes=True)


class BaseModelSchema(BaseSchema):
    """Base schema for database models."""
    id: UUID
    created_at: datetime
    updated_at: datetime


class ResponseSchema(BaseSchema):
    """Standard API response schema."""
    status: str
    message: Optional[str] = None
    data: Optional[dict] = None