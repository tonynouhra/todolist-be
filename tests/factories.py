"""
Test data factories for generating test objects.

This module provides Factory Boy factories for creating test data objects
with realistic default values and easy customization.
"""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
import factory
from factory.alchemy import SQLAlchemyModelFactory

from models import User, Todo, Project, AIInteraction


class UserFactory(SQLAlchemyModelFactory):
    """Factory for creating User test instances."""

    class Meta:
        model = User
        sqlalchemy_session = None  # Will be set at runtime
        sqlalchemy_session_persistence = "commit"

    clerk_user_id = factory.LazyFunction(lambda: f"clerk_user_{uuid.uuid4()}")
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    username = factory.Sequence(lambda n: f"testuser{n}")
    is_active = True


class ProjectFactory(SQLAlchemyModelFactory):
    """Factory for creating Project test instances."""

    class Meta:
        model = Project
        sqlalchemy_session = None  # Will be set at runtime
        sqlalchemy_session_persistence = "commit"

    name = factory.Sequence(lambda n: f"Test Project {n}")
    description = factory.Faker("text", max_nb_chars=200)
    # user_id will be passed when creating the project


class TodoFactory(SQLAlchemyModelFactory):
    """Factory for creating Todo test instances."""

    class Meta:
        model = Todo
        sqlalchemy_session = None  # Will be set at runtime
        sqlalchemy_session_persistence = "commit"

    title = factory.Faker("sentence", nb_words=4, variable_nb_words=True)
    description = factory.Faker("text", max_nb_chars=500)
    status = factory.Iterator(["todo", "in_progress", "done"])
    priority = factory.Faker("random_int", min=1, max=5)
    due_date = factory.LazyFunction(lambda: datetime.now(timezone.utc) + timedelta(days=7))
    ai_generated = False
    # user_id, project_id, parent_todo_id will be passed when creating

    @factory.post_generation
    def set_completed_at(self, create, extracted, **kwargs):
        """Set completed_at if status is done."""
        if self.status == "done":
            self.completed_at = datetime.now(timezone.utc)


class SubtaskFactory(TodoFactory):
    """Factory for creating subtask Todo instances."""

    ai_generated = True
    parent_todo_id = factory.LazyAttribute(lambda obj: uuid.uuid4())


class AIInteractionFactory(SQLAlchemyModelFactory):
    """Factory for creating AI interaction test instances."""

    class Meta:
        model = AIInteraction
        sqlalchemy_session = None  # Will be set at runtime
        sqlalchemy_session_persistence = "commit"

    prompt = factory.Faker("sentence", nb_words=10)
    response = factory.LazyFunction(
        lambda: '{"subtasks": [{"title": "Test subtask", "priority": 3}]}'
    )
    interaction_type = factory.Iterator(
        ["subtask_generation", "file_analysis", "task_optimization"]
    )
    # user_id and todo_id will be passed when creating


# Utility functions for creating test data
async def create_user_with_todos(
    session, num_todos: int = 3, **user_kwargs
) -> tuple[User, list[Todo]]:
    """Create a user with a specified number of todos."""
    UserFactory._meta.sqlalchemy_session = session
    TodoFactory._meta.sqlalchemy_session = session

    user = UserFactory.create(**user_kwargs)
    todos = []

    for i in range(num_todos):
        todo = TodoFactory.create(user_id=user.id)
        todos.append(todo)

    await session.commit()
    return user, todos


async def create_project_with_todos(
    session, user_id: uuid.UUID, num_todos: int = 5
) -> tuple[Project, list[Todo]]:
    """Create a project with a specified number of todos."""
    ProjectFactory._meta.sqlalchemy_session = session
    TodoFactory._meta.sqlalchemy_session = session

    project = ProjectFactory.create(user_id=user_id)
    todos = []

    for i in range(num_todos):
        todo = TodoFactory.create(user_id=user_id, project_id=project.id)
        todos.append(todo)

    await session.commit()
    return project, todos


async def create_todo_with_subtasks(
    session,
    user_id: uuid.UUID,
    num_subtasks: int = 3,
    project_id: Optional[uuid.UUID] = None,
) -> tuple[Todo, list[Todo]]:
    """Create a parent todo with a specified number of subtasks."""
    TodoFactory._meta.sqlalchemy_session = session
    SubtaskFactory._meta.sqlalchemy_session = session

    parent_todo = TodoFactory.create(user_id=user_id, project_id=project_id, status="in_progress")

    subtasks = []
    for i in range(num_subtasks):
        subtask = SubtaskFactory.create(
            user_id=user_id, parent_todo_id=parent_todo.id, project_id=project_id
        )
        subtasks.append(subtask)

    await session.commit()
    return parent_todo, subtasks


async def create_mixed_status_todos(
    session, user_id: uuid.UUID, project_id: Optional[uuid.UUID] = None
) -> list[Todo]:
    """Create todos with different statuses for testing."""
    TodoFactory._meta.sqlalchemy_session = session

    todos = []

    # Create one todo of each status
    for status in ["todo", "in_progress", "done"]:
        todo = TodoFactory.create(user_id=user_id, project_id=project_id, status=status)
        todos.append(todo)

    # Create an overdue todo
    overdue_todo = TodoFactory.create(
        user_id=user_id,
        project_id=project_id,
        status="todo",
        due_date=datetime.now(timezone.utc) - timedelta(days=1),
        priority=5,
    )
    todos.append(overdue_todo)

    await session.commit()
    return todos
