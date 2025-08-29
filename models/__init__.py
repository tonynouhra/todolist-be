"""
Models package initialization.
"""

from .ai_interaction import AIInteraction
from .base import Base, BaseModel
from .file import File
from .project import Project
from .todo import Todo

# New partitioned models
from .todo_partitioned import AITodoInteraction, TodoActive, TodoArchived
from .user import User

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
