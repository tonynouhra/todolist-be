"""
Chat message model for AI assistant messages.
"""

from sqlalchemy import Boolean, Column, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
import enum

from .base import UUID, BaseModel


class MessageRole(str, enum.Enum):
    """Message role enumeration."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    """
    Represents a chat message entity in the application.
    """

    __tablename__ = "chat_messages"

    conversation_id = Column(UUID(), ForeignKey("chat_conversations.id"), nullable=False)
    role = Column(Enum(MessageRole), nullable=False)
    content = Column(Text, nullable=False)

    # Optional: Store actions taken by AI (e.g., created project, task, etc.)
    actions = Column(JSONB, nullable=True)  # {"type": "create_project", "data": {...}}

    # Whether this message led to action execution
    has_actions = Column(Boolean, default=False)

    # Relationships
    conversation = relationship("ChatConversation", back_populates="messages")
