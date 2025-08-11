"""
A module defining the `tod` ORM model representing a to-do item.

This module includes the SQLAlchemy ORM model `Tod`, which represents a
to-do item along with its attributes for database use. It is part of a to-do
management system. The model contains relationships with other entities such
as users, projects, subtasks, and files.

Classes:
    Tod: Represents a single to-do item with properties like title, status,
    priority, due date, and relationships with users, projects, subtasks,
    and files.
"""

from sqlalchemy import Column, String, Text, Integer, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, backref
from .base import BaseModel


class Todo(BaseModel):
    __tablename__ = "todos"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"))
    parent_todo_id = Column(UUID(as_uuid=True), ForeignKey("todos.id"))

    title = Column(String(500), nullable=False)
    description = Column(Text)
    status = Column(String(20), default="todo")  # todo, in_progress, done
    priority = Column(Integer, default=3)  # 1-5 scale
    due_date = Column(DateTime)
    completed_at = Column(DateTime)
    ai_generated = Column(Boolean, default=False)

    # Relationships
    user = relationship("User", back_populates="todos")
    project = relationship("Project", back_populates="todos")
    subtasks = relationship(
        "Todo",
        backref=backref("parent", remote_side="Todo.id"),
        foreign_keys=[parent_todo_id],
    )
    files = relationship("File", back_populates="todo")