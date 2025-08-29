# ruff: noqa: F403, F401
"""Schemas package initialization."""

# Import all schemas to ensure they're registered
from .base import *

# Rebuild models to resolve forward references
from .project import *
from .project import ProjectWithTodos
from .todo import *
from .todo import TodoWithSubtasks
from .user import *

# Rebuild models after all schemas are loaded
ProjectWithTodos.model_rebuild()
TodoWithSubtasks.model_rebuild()
