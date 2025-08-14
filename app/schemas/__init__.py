"""Schemas package initialization."""

# Import all schemas to ensure they're registered
from .base import *
from .user import *
from .todo import *
from .project import *

# Rebuild models to resolve forward references
from .project import ProjectWithTodos
from .todo import TodoWithSubtasks

# Rebuild models after all schemas are loaded
ProjectWithTodos.model_rebuild()
TodoWithSubtasks.model_rebuild()