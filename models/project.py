"""
Project model for organizing todos.
"""

from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModel


class Project(BaseModel):
    """
    Represents a project entity in the application.
    """
    __tablename__ = "projects"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Relationships
    user = relationship("User", back_populates="projects")
    todos = relationship("Todo", back_populates="project", cascade="all, delete-orphan")