"""Todo schemas for request/response serialization."""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from .base import BaseSchema, BaseModelSchema


class TodoBase(BaseSchema):
    """Base todo schema with common fields."""
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    status: str = Field(default="todo", pattern="^(todo|in_progress|done)$")
    priority: int = Field(default=3, ge=1, le=5)
    due_date: Optional[datetime] = None
    ai_generated: bool = Field(default=False)


class TodoCreate(TodoBase):
    """Schema for creating a new todo."""
    project_id: Optional[UUID] = None
    parent_todo_id: Optional[UUID] = None
    generate_ai_subtasks: bool = Field(default=False)


class TodoUpdate(BaseSchema):
    """Schema for updating a todo."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    status: Optional[str] = Field(None, pattern="^(todo|in_progress|done)$")
    priority: Optional[int] = Field(None, ge=1, le=5)
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TodoResponse(BaseModelSchema):
    """Schema for todo response."""
    user_id: UUID
    project_id: Optional[UUID] = None
    parent_todo_id: Optional[UUID] = None
    title: str
    description: Optional[str] = None
    status: str
    priority: int
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    ai_generated: bool
    
    model_config = ConfigDict(from_attributes=True)


class TodoWithSubtasks(TodoResponse):
    """Schema for todo with expanded subtasks."""
    subtasks: List[TodoResponse] = []


class TodoFilter(BaseSchema):
    """Schema for filtering todos."""
    status: Optional[str] = Field(None, pattern="^(todo|in_progress|done)$")
    priority: Optional[int] = Field(None, ge=1, le=5)
    project_id: Optional[UUID] = None
    parent_todo_id: Optional[UUID] = None
    ai_generated: Optional[bool] = None
    due_date_from: Optional[datetime] = None
    due_date_to: Optional[datetime] = None
    search: Optional[str] = None


class TodoListResponse(BaseSchema):
    """Schema for todo list response."""
    todos: List[TodoResponse]
    total: int
    page: int
    size: int
    has_next: bool
    has_prev: bool


# Update forward references
TodoWithSubtasks.model_rebuild()