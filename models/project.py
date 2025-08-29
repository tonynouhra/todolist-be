"""
Project model for organizing todos.
"""

from sqlalchemy import Column, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from .base import UUID, BaseModel


class Project(BaseModel):
    """
    Represents a project entity in the application.
    """

    __tablename__ = "projects"

    user_id = Column(UUID(), ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)

    # Relationships
    user = relationship("User", back_populates="projects")

    # Keep original todos relationship for backward compatibility during migration
    todos = relationship("Todo", back_populates="project", cascade="all, delete-orphan")

    # New partitioned relationships
    active_todos = relationship(
        "TodoActive", back_populates="project", cascade="all, delete-orphan"
    )
    archived_todos = relationship(
        "TodoArchived", back_populates="project", cascade="all, delete-orphan"
    )
