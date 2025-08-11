"""
AI interaction model for storing AI conversation history.
"""

from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModel


class AIInteraction(BaseModel):
    """
    Represents an AI interaction entity in the application.
    """
    __tablename__ = "ai_interactions"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    todo_id = Column(UUID(as_uuid=True), ForeignKey("todos.id"))
    prompt = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    interaction_type = Column(String(50))  # subtask_generation, file_analysis, etc.

    # Relationships
    user = relationship("User")
    todo = relationship("Todo")