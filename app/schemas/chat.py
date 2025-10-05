"""Chat schemas for request/response serialization."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import UUID

from pydantic import ConfigDict, Field

from .base import BaseModelSchema, BaseSchema


class MessageRole(str, Enum):
    """Message role enumeration."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatAction(BaseSchema):
    """Schema for actions taken by AI assistant."""

    action_type: str = Field(..., description="Type of action (create_project, create_task, etc.)")
    data: dict = Field(..., description="Action-specific data")
    success: bool = Field(default=True, description="Whether action was successful")
    error_message: str | None = Field(None, description="Error message if action failed")


class ChatMessageCreate(BaseSchema):
    """Schema for creating a chat message."""

    conversation_id: UUID | None = Field(None, description="ID of existing conversation, null for new")
    content: str = Field(..., min_length=1, max_length=10000, description="Message content")
    role: MessageRole = Field(default=MessageRole.USER, description="Message role")


class ChatMessageResponse(BaseModelSchema):
    """Schema for chat message response."""

    conversation_id: UUID
    role: MessageRole
    content: str
    actions: list[ChatAction] | None = Field(None, description="Actions taken by assistant")
    has_actions: bool = Field(default=False)

    model_config = ConfigDict(from_attributes=True)


class ChatConversationCreate(BaseSchema):
    """Schema for creating a new conversation."""

    title: str | None = Field(None, max_length=255, description="Optional conversation title")
    initial_message: str | None = Field(None, description="Optional initial message")


class ChatConversationResponse(BaseModelSchema):
    """Schema for chat conversation response."""

    user_id: UUID
    title: str | None
    summary: str | None
    message_count: int = Field(default=0, description="Number of messages in conversation")

    model_config = ConfigDict(from_attributes=True)


class ChatConversationDetailResponse(ChatConversationResponse):
    """Schema for detailed chat conversation response with messages."""

    messages: list[ChatMessageResponse] = Field(default=[], description="Conversation messages")

    model_config = ConfigDict(from_attributes=True)


class ChatRequest(BaseSchema):
    """Schema for chat request."""

    conversation_id: UUID | None = Field(None, description="Existing conversation ID, null for new")
    message: str = Field(..., min_length=1, max_length=10000, description="User message")
    context: dict | None = Field(None, description="Additional context (current project, tasks, etc.)")


class ChatResponse(BaseSchema):
    """Schema for chat response."""

    conversation_id: UUID
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse
    actions_taken: list[ChatAction] = Field(default=[], description="Actions executed by assistant")
    timestamp: datetime


class ChatHistoryResponse(BaseSchema):
    """Schema for chat history response."""

    conversations: list[ChatConversationResponse]
    total: int
    page: int
    size: int
    has_next: bool
    has_prev: bool


class SuggestedAction(BaseSchema):
    """Schema for AI-suggested actions."""

    action_type: str = Field(..., description="create_project, create_task, create_subtasks")
    title: str = Field(..., description="Suggested title")
    description: str | None = None
    priority: int | None = Field(None, ge=1, le=5)
    additional_data: dict = Field(default={}, description="Additional action-specific data")
    confirmation_required: bool = Field(default=True, description="Whether user confirmation needed")


class ChatSuggestionResponse(BaseSchema):
    """Schema for chat with suggested actions."""

    message: str = Field(..., description="AI response message")
    suggested_actions: list[SuggestedAction] = Field(
        default=[], description="Suggested actions for user to approve"
    )


# Update forward references if needed
ChatConversationDetailResponse.model_rebuild()
ChatResponse.model_rebuild()
