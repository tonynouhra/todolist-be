"""
Models package initialization.
"""

from .ai_interaction import AIInteraction
from .base import Base, BaseModel
from .chat_conversation import ChatConversation
from .chat_message import ChatMessage
from .file import File
from .project import Project
from .todo import Todo

# New partitioned models
from .todo_partitioned import AITodoInteraction, TodoActive, TodoArchived
from .user import User
from .user_settings import UserSettings

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
    "UserSettings",
    # Chat models
    "ChatConversation",
    "ChatMessage",
]
