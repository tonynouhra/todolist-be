# tests/conftest.py
import pytest
import pytest_asyncio
import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from unittest.mock import MagicMock, AsyncMock

from app.main import app
from app.database import get_db
from app.core.dependencies import get_current_user
from models import Base, User, Todo, Project, AIInteraction

# Test database URL - Use environment variable or default
import os
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test_ai_todo")


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def test_db():
    """Create a test database session."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    TestSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

    # Clean up - drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def client(test_db):
    """Create a test client with database dependency override."""
    app.dependency_overrides[get_db] = lambda: test_db
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def authenticated_client(test_db, test_user):
    """Create an authenticated test client."""
    def override_get_current_user():
        return test_user
    
    app.dependency_overrides[get_db] = lambda: test_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


# User fixtures
@pytest.fixture
async def test_user(test_db):
    """Create a test user."""
    user = User(
        clerk_user_id=f"clerk_user_{uuid.uuid4()}",
        email="test@example.com",
        username="testuser",
        is_active=True
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_user_2(test_db):
    """Create a second test user."""
    user = User(
        clerk_user_id=f"clerk_user_{uuid.uuid4()}",
        email="test2@example.com",
        username="testuser2",
        is_active=True
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


# Project fixtures
@pytest.fixture
async def test_project(test_db, test_user):
    """Create a test project."""
    project = Project(
        user_id=test_user.id,
        name="Test Project",
        description="A test project for testing"
    )
    test_db.add(project)
    await test_db.commit()
    await test_db.refresh(project)
    return project


@pytest.fixture
async def test_project_2(test_db, test_user):
    """Create a second test project."""
    project = Project(
        user_id=test_user.id,
        name="Test Project 2",
        description="Another test project"
    )
    test_db.add(project)
    await test_db.commit()
    await test_db.refresh(project)
    return project


# Todo fixtures
@pytest.fixture
async def test_todo(test_db, test_user, test_project):
    """Create a test todo."""
    todo = Todo(
        user_id=test_user.id,
        project_id=test_project.id,
        title="Test Todo",
        description="A test todo item",
        status="todo",
        priority=3,
        due_date=datetime.now(timezone.utc) + timedelta(days=7),
        ai_generated=False
    )
    test_db.add(todo)
    await test_db.commit()
    await test_db.refresh(todo)
    return todo


@pytest.fixture
async def test_todo_with_subtasks(test_db, test_user, test_project):
    """Create a test todo with subtasks."""
    parent_todo = Todo(
        user_id=test_user.id,
        project_id=test_project.id,
        title="Parent Todo",
        description="A parent todo with subtasks",
        status="in_progress",
        priority=4,
        ai_generated=False
    )
    test_db.add(parent_todo)
    await test_db.flush()  # Get the ID without committing
    
    # Create subtasks
    subtask1 = Todo(
        user_id=test_user.id,
        project_id=test_project.id,
        parent_todo_id=parent_todo.id,
        title="Subtask 1",
        description="First subtask",
        status="todo",
        priority=3,
        ai_generated=True
    )
    
    subtask2 = Todo(
        user_id=test_user.id,
        project_id=test_project.id,
        parent_todo_id=parent_todo.id,
        title="Subtask 2",
        description="Second subtask",
        status="done",
        priority=2,
        ai_generated=True,
        completed_at=datetime.now(timezone.utc)
    )
    
    test_db.add_all([subtask1, subtask2])
    await test_db.commit()
    await test_db.refresh(parent_todo)
    return parent_todo


@pytest.fixture
async def completed_todo(test_db, test_user):
    """Create a completed todo."""
    todo = Todo(
        user_id=test_user.id,
        title="Completed Todo",
        description="A completed todo item",
        status="done",
        priority=5,
        ai_generated=False,
        completed_at=datetime.now(timezone.utc)
    )
    test_db.add(todo)
    await test_db.commit()
    await test_db.refresh(todo)
    return todo


@pytest.fixture
async def overdue_todo(test_db, test_user):
    """Create an overdue todo."""
    todo = Todo(
        user_id=test_user.id,
        title="Overdue Todo",
        description="An overdue todo item",
        status="todo",
        priority=5,
        due_date=datetime.now(timezone.utc) - timedelta(days=1),
        ai_generated=False
    )
    test_db.add(todo)
    await test_db.commit()
    await test_db.refresh(todo)
    return todo


# AI fixtures
@pytest.fixture
async def ai_interaction(test_db, test_user, test_todo):
    """Create a test AI interaction."""
    interaction = AIInteraction(
        user_id=test_user.id,
        todo_id=test_todo.id,
        prompt="Generate subtasks for: Test Todo",
        response='{"subtasks": [{"title": "Subtask 1", "priority": 3}]}',
        interaction_type="subtask_generation"
    )
    test_db.add(interaction)
    await test_db.commit()
    await test_db.refresh(interaction)
    return interaction


# Mock fixtures for external services
@pytest.fixture
def mock_clerk_auth():
    """Mock Clerk authentication."""
    mock = MagicMock()
    mock.verify_token = AsyncMock(return_value={
        "sub": "clerk_user_123",
        "email": "test@example.com",
        "username": "testuser"
    })
    return mock


@pytest.fixture
def mock_ai_service():
    """Mock AI service for testing."""
    mock = MagicMock()
    mock.generate_subtasks = AsyncMock()
    mock.analyze_file = AsyncMock()
    mock.get_service_status = AsyncMock()
    return mock


# Utility fixtures
@pytest.fixture
def sample_subtask_response():
    """Sample AI subtask generation response."""
    return {
        "subtasks": [
            {
                "title": "Research the topic",
                "description": "Gather information and resources",
                "priority": 4,
                "estimated_time": "2 hours",
                "order": 1
            },
            {
                "title": "Create an outline",
                "description": "Structure the main points",
                "priority": 3,
                "estimated_time": "1 hour",
                "order": 2
            },
            {
                "title": "Write the content",
                "description": "Draft the main content",
                "priority": 5,
                "estimated_time": "4 hours",
                "order": 3
            }
        ]
    }


@pytest.fixture
def sample_file_analysis_response():
    """Sample AI file analysis response."""
    return {
        "summary": "This document contains project requirements and specifications.",
        "key_points": [
            "User authentication required",
            "Database schema includes users and todos",
            "API endpoints for CRUD operations"
        ],
        "suggested_tasks": [
            "Implement user registration",
            "Set up database migrations",
            "Create API endpoints"
        ],
        "confidence": 0.85
    }