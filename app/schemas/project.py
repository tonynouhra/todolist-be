"""Project schemas for request/response serialization."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator

from .base import BaseModelSchema, BaseSchema


class ProjectBase(BaseSchema):
    """Base project schema with common fields."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and clean the project name."""
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError('Project name cannot be empty or only whitespace')
        return v


class ProjectCreate(ProjectBase):
    """Schema for creating a new project."""

    pass


class ProjectUpdate(BaseSchema):
    """Schema for updating a project."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate and clean the project name."""
        if v is not None and isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError('Project name cannot be empty or only whitespace')
        return v


class ProjectResponse(BaseModelSchema):
    """Schema for project response."""

    user_id: UUID
    name: str
    description: Optional[str] = None

    # Computed fields
    todo_count: Optional[int] = None
    completed_todo_count: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class ProjectWithTodos(ProjectResponse):
    """Schema for project with todos."""

    todos: List[TodoResponse] = []


class ProjectFilter(BaseSchema):
    """Schema for filtering projects."""

    search: Optional[str] = None


class ProjectListResponse(BaseSchema):
    """Schema for project list response."""

    projects: List[ProjectResponse]
    total: int
    page: int
    size: int
    has_next: bool
    has_prev: bool


class ProjectStats(BaseSchema):
    """Schema for project statistics."""

    total_projects: int
    projects_with_todos: int
    average_todos_per_project: float


# Import TodoResponse at the end to avoid circular imports
from .todo import TodoResponse

# Rebuild the model to resolve forward references
ProjectWithTodos.model_rebuild()
