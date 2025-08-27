"""Todo schemas for request/response serialization."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict, Field

from .base import BaseModelSchema, BaseSchema


class TodoBase(BaseSchema):
    """Base todo schema with common fields."""

    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    status: str = Field(default="todo", pattern="^(todo|in_progress|done)$")
    priority: int = Field(default=3, ge=1, le=5)
    due_date: datetime | None = None
    ai_generated: bool = Field(default=False)


class TodoCreate(TodoBase):
    """Schema for creating a new todo."""

    project_id: UUID | None = None
    parent_todo_id: UUID | None = None
    generate_ai_subtasks: bool = Field(default=False)


class TodoUpdate(BaseSchema):
    """Schema for updating a todo."""

    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = None
    status: str | None = Field(None, pattern="^(todo|in_progress|done)$")
    priority: int | None = Field(None, ge=1, le=5)
    due_date: datetime | None = None
    completed_at: datetime | None = None
    project_id: UUID | None = None


class TodoResponse(BaseModelSchema):
    """Schema for todo response."""

    user_id: UUID
    project_id: UUID | None = None
    parent_todo_id: UUID | None = None
    title: str
    description: str | None = None
    status: str
    priority: int
    due_date: datetime | None = None
    completed_at: datetime | None = None
    ai_generated: bool

    model_config = ConfigDict(from_attributes=True)


class TodoWithSubtasks(TodoResponse):
    """Schema for todo with expanded subtasks."""

    subtasks: list[TodoResponse] = []


class TodoFilter(BaseSchema):
    """Schema for filtering todos."""

    status: str | None = Field(None, pattern="^(todo|in_progress|done)$")
    priority: int | None = Field(None, ge=1, le=5)
    project_id: UUID | None = None
    parent_todo_id: UUID | None = None
    ai_generated: bool | None = None
    due_date_from: datetime | None = None
    due_date_to: datetime | None = None
    search: str | None = None


class TodoListResponse(BaseSchema):
    """Schema for todo list response."""

    todos: list[TodoResponse]
    total: int
    page: int
    size: int
    has_next: bool
    has_prev: bool


# Update forward references
TodoWithSubtasks.model_rebuild()
