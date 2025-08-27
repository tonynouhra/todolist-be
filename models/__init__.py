"""
Models package initialization.
"""

from .base import Base, BaseModel
from .user import User
from .project import Project
from .todo import Todo
from .file import File
from .ai_interaction import AIInteraction

# New partitioned models
from .todo_partitioned import TodoActive, TodoArchived, AITodoInteraction

__all__ = [
    "Base",
    "BaseModel",
    "User",
    "Project",
    "Todo",
    "File",
    "AIInteraction",
    # Partitioned models
    "TodoActive",
    "TodoArchived",
    "AITodoInteraction",
]
