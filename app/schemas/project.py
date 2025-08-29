"""Project schemas for request/response serialization."""

from __future__ import annotations

from uuid import UUID

from pydantic import ConfigDict, Field, field_validator

from .base import BaseModelSchema, BaseSchema


class ProjectBase(BaseSchema):
    """Base project schema with common fields."""

    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and clean the project name."""
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Project name cannot be empty or only whitespace")
        return v


class ProjectCreate(ProjectBase):
    """Schema for creating a new project."""


class ProjectUpdate(BaseSchema):
    """Schema for updating a project."""

    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        """Validate and clean the project name."""
        if v is not None and isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Project name cannot be empty or only whitespace")
        return v


class ProjectResponse(BaseModelSchema):
    """Schema for project response."""

    user_id: UUID
    name: str
    description: str | None = None

    # Computed fields
    todo_count: int | None = None
    completed_todo_count: int | None = None

    model_config = ConfigDict(from_attributes=True)


class ProjectWithTodos(ProjectResponse):
    """Schema for project with todos."""

    todos: list[TodoResponse] = []


class ProjectFilter(BaseSchema):
    """Schema for filtering projects."""

    search: str | None = None


class ProjectListResponse(BaseSchema):
    """Schema for project list response."""

    projects: list[ProjectResponse]
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
from .todo import TodoResponse  # noqa: E402, I001

# Rebuild the model to resolve forward references
ProjectWithTodos.model_rebuild()
