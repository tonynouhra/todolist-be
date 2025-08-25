"""AI schemas for request/response serialization."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .base import BaseModelSchema, BaseSchema


class SubtaskGenerationRequest(BaseSchema):
    """Schema for requesting AI subtask generation for an existing todo."""

    todo_id: UUID = Field(..., description="ID of the existing todo to generate subtasks for")
    max_subtasks: int = Field(
        default=5, ge=3, le=7, description="Maximum number of subtasks to generate"
    )


class GeneratedSubtask(BaseSchema):
    """Schema for a generated subtask."""

    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    priority: int = Field(default=3, ge=1, le=5)
    estimated_time: Optional[str] = Field(
        None, description="Estimated time to complete (e.g., '30 minutes', '2 hours')"
    )
    order: int = Field(..., ge=1, description="Suggested order of completion")


class SubtaskGenerationResponse(BaseSchema):
    """Schema for AI subtask generation response."""

    parent_task_title: str
    generated_subtasks: List[GeneratedSubtask]
    total_subtasks: int
    generation_timestamp: datetime
    ai_model: str = Field(default="gemini-1.5-flash", alias="model_used")


class FileAnalysisRequest(BaseSchema):
    """Schema for requesting AI file analysis."""

    file_id: UUID
    analysis_type: str = Field(default="general", pattern="^(general|task_extraction|summary)$")
    context: Optional[str] = Field(None, description="Additional context for analysis")


class FileAnalysisResponse(BaseSchema):
    """Schema for AI file analysis response."""

    file_id: UUID
    analysis_type: str
    summary: str
    key_points: List[str] = []
    suggested_tasks: List[str] = []
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="AI confidence in analysis")
    analysis_timestamp: datetime
    ai_model: str = Field(default="gemini-1.5-flash", alias="model_used")


class AIInteractionResponse(BaseModelSchema):
    """Schema for AI interaction history response."""

    user_id: UUID
    todo_id: Optional[UUID] = None
    prompt: str
    response: str
    interaction_type: str

    model_config = ConfigDict(from_attributes=True)


class AIInteractionListResponse(BaseSchema):
    """Schema for AI interaction list response."""

    interactions: List[AIInteractionResponse]
    total: int
    page: int
    size: int
    has_next: bool
    has_prev: bool


class AIServiceStatus(BaseSchema):
    """Schema for AI service status."""

    service_available: bool
    model_name: str
    last_request_timestamp: Optional[datetime] = None
    requests_today: int = Field(default=0, description="Number of requests made today")
    quota_remaining: Optional[int] = Field(None, description="Remaining API quota if available")


class AIErrorResponse(BaseSchema):
    """Schema for AI service errors."""

    error_code: str
    error_message: str
    retry_after: Optional[int] = Field(None, description="Seconds to wait before retrying")
    suggestions: List[str] = []


# Update forward references if needed
SubtaskGenerationResponse.model_rebuild()
FileAnalysisResponse.model_rebuild()
