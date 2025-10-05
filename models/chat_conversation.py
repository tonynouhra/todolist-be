"""
Chat conversation model for AI assistant conversations.
"""

from sqlalchemy import Column, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from .base import UUID, BaseModel


class ChatConversation(BaseModel):
    """
    Represents a chat conversation entity in the application.
    """

    __tablename__ = "chat_conversations"

    user_id = Column(UUID(), ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=True)  # Auto-generated from first message
    summary = Column(Text, nullable=True)  # AI-generated summary of conversation

    # Relationships
    user = relationship("User", back_populates="chat_conversations")
    messages = relationship(
        "ChatMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )
