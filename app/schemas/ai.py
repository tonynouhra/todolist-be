"""AI schemas for request/response serialization."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator

from .base import BaseModelSchema, BaseSchema


class SubtaskGenerationRequest(BaseSchema):
    """Schema for requesting AI subtask generation for an existing todo."""

    todo_id: UUID = Field(..., description="ID of the existing todo to generate subtasks for")
    min_subtasks: int = Field(
        default=3, ge=1, le=5, description="Minimum number of subtasks to generate"
    )
    max_subtasks: int = Field(
        default=5, ge=3, le=5, description="Maximum number of subtasks to generate"
    )

    @field_validator('max_subtasks')
    @classmethod
    def validate_subtask_range(cls, v, info):
        """Ensure max_subtasks is greater than or equal to min_subtasks."""
        if 'min_subtasks' in info.data and v < info.data['min_subtasks']:
            raise ValueError('max_subtasks must be greater than or equal to min_subtasks')
        return v


class GeneratedSubtask(BaseSchema):
    """Schema for a generated subtask."""

    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    priority: int = Field(default=3, ge=1, le=5)
    estimated_time: str | None = Field(
        None, description="Estimated time to complete (e.g., '30 minutes', '2 hours')"
    )
    order: int = Field(..., ge=1, description="Suggested order of completion")


class SubtaskGenerationResponse(BaseSchema):
    """Schema for AI subtask generation response."""

    parent_task_title: str
    generated_subtasks: list[GeneratedSubtask]
    total_subtasks: int
    generation_timestamp: datetime
    ai_model: str = Field(default="gemini-1.5-flash", alias="model_used")


class FileAnalysisRequest(BaseSchema):
    """Schema for requesting AI file analysis."""

    file_id: UUID
    analysis_type: str = Field(default="general", pattern="^(general|task_extraction|summary)$")
    context: str | None = Field(None, description="Additional context for analysis")


class FileAnalysisResponse(BaseSchema):
    """Schema for AI file analysis response."""

    file_id: UUID
    analysis_type: str
    summary: str
    key_points: list[str] = []
    suggested_tasks: list[str] = []
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="AI confidence in analysis")
    analysis_timestamp: datetime
    ai_model: str = Field(default="gemini-1.5-flash", alias="model_used")


class AIInteractionResponse(BaseModelSchema):
    """Schema for AI interaction history response."""

    user_id: UUID
    todo_id: UUID | None = None
    prompt: str
    response: str
    interaction_type: str

    model_config = ConfigDict(from_attributes=True)


class AIInteractionListResponse(BaseSchema):
    """Schema for AI interaction list response."""

    interactions: list[AIInteractionResponse]
    total: int
    page: int
    size: int
    has_next: bool
    has_prev: bool


class AIServiceStatus(BaseSchema):
    """Schema for AI service status."""

    service_available: bool
    model_name: str
    last_request_timestamp: datetime | None = None
    requests_today: int = Field(default=0, description="Number of requests made today")
    quota_remaining: int | None = Field(None, description="Remaining API quota if available")


class TodoSuggestionRequest(BaseSchema):
    """Schema for requesting AI todo suggestions."""

    project_id: UUID | None = Field(None, description="ID of project to generate todos for")
    user_input: str = Field(..., min_length=1, description="Description of what user wants to accomplish")
    existing_todos: list[str] = Field(default=[], description="List of existing todo titles for context")
    max_todos: int = Field(default=5, ge=1, le=10, description="Maximum number of todos to generate")


class GeneratedTodo(BaseSchema):
    """Schema for a generated todo suggestion."""

    title: str = Field(..., min_length=1, max_length=500)
    description: str | None = None
    priority: int = Field(default=3, ge=1, le=5)
    estimated_time: str | None = Field(
        None, description="Estimated time to complete (e.g., '30 minutes', '2 hours')"
    )
    category: str | None = Field(None, description="Suggested category for the todo")


class TodoSuggestionResponse(BaseSchema):
    """Schema for AI todo suggestions response."""

    request_description: str
    generated_todos: list[GeneratedTodo]
    total_todos: int
    generation_timestamp: datetime
    ai_model: str = Field(default="gemini-1.5-flash", alias="model_used")


class TaskOptimizationRequest(BaseSchema):
    """Schema for requesting AI task optimization."""

    todo_id: UUID | None = Field(None, description="ID of existing todo to optimize")
    current_title: str | None = Field(None, description="Current task title")
    current_description: str | None = Field(None, description="Current task description")
    optimization_type: str = Field(
        default="description",
        pattern="^(description|title|both|clarity|detail)$",
        description="Type of optimization to perform"
    )
    context: str | None = Field(None, description="Additional context for optimization")


class TaskOptimizationResponse(BaseSchema):
    """Schema for AI task optimization response."""

    original_title: str | None
    original_description: str | None
    optimized_title: str | None
    optimized_description: str | None
    optimization_type: str
    improvements: list[str] = Field(default=[], description="List of improvements made")
    optimization_timestamp: datetime
    ai_model: str = Field(default="gemini-1.5-flash", alias="model_used")


class AIErrorResponse(BaseSchema):
    """Schema for AI service errors."""

    error_code: str
    error_message: str
    retry_after: int | None = Field(None, description="Seconds to wait before retrying")
    suggestions: list[str] = []


# Update forward references if needed
SubtaskGenerationResponse.model_rebuild()
FileAnalysisResponse.model_rebuild()
TodoSuggestionResponse.model_rebuild()
TaskOptimizationResponse.model_rebuild()
