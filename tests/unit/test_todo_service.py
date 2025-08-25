"""
Unit tests for TodoService.

This module contains comprehensive unit tests for the TodoService class,
testing all business logic methods including hierarchical todos, AI integration,
and various filtering scenarios.
"""

import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, AsyncMock

from app.domains.todo.service import TodoService
from app.schemas.todo import TodoCreate, TodoUpdate, TodoFilter
from app.shared.pagination import PaginationParams
from app.exceptions.todo import (
    TodoNotFoundError,
    TodoPermissionError,
    InvalidTodoOperationError,
    MaxTodoDepthExceededError,
)
from models.todo import Todo


class TestTodoService:
    """Test cases for TodoService."""

    @pytest.mark.asyncio
    async def test_create_todo_success(self, test_db, test_user, test_project):
        """Test successful todo creation."""
        service = TodoService(test_db)
        todo_data = TodoCreate(
            title="Test Todo",
            description="A test todo",
            status="todo",
            priority=3,
            project_id=test_project.id,
            due_date=datetime.now(timezone.utc) + timedelta(days=7),
        )

        result = await service.create_todo(todo_data, test_user.id)

        assert result is not None
        assert result.title == "Test Todo"
        assert result.description == "A test todo"
        assert result.status == "todo"
        assert result.priority == 3
        assert result.user_id == test_user.id
        assert result.project_id == test_project.id
        assert result.ai_generated is False

    @pytest.mark.asyncio
    async def test_create_todo_minimal_data(self, test_db, test_user):
        """Test todo creation with minimal required data."""
        service = TodoService(test_db)
        todo_data = TodoCreate(title="Minimal Todo")

        result = await service.create_todo(todo_data, test_user.id)

        assert result is not None
        assert result.title == "Minimal Todo"
        assert result.description is None
        assert result.status == "todo"
        assert result.priority == 3
        assert result.user_id == test_user.id
        assert result.project_id is None
        assert result.parent_todo_id is None

    @pytest.mark.asyncio
    async def test_create_subtask_success(self, test_db, test_user, test_project, test_todo):
        """Test creating a subtask."""
        service = TodoService(test_db)
        subtask_data = TodoCreate(title="Subtask", parent_todo_id=test_todo.id, priority=2)

        result = await service.create_todo(subtask_data, test_user.id)

        assert result is not None
        assert result.title == "Subtask"
        assert result.parent_todo_id == test_todo.id
        assert result.user_id == test_user.id
        assert result.priority == 2

    @pytest.mark.asyncio
    async def test_create_subtask_nonexistent_parent(self, test_db, test_user):
        """Test creating subtask with non-existent parent."""
        service = TodoService(test_db)
        fake_parent_id = uuid.uuid4()
        subtask_data = TodoCreate(title="Orphan Subtask", parent_todo_id=fake_parent_id)

        with pytest.raises(TodoNotFoundError):
            await service.create_todo(subtask_data, test_user.id)

    @pytest.mark.asyncio
    async def test_create_subtask_max_depth_exceeded(self, test_db, test_user):
        """Test creating subtask beyond maximum depth."""
        service = TodoService(test_db)

        # Create a chain of nested todos (depth 5)
        current_todo = None
        for i in range(6):  # This will create depth of 5 + 1 (exceeding limit)
            todo_data = TodoCreate(
                title=f"Todo Level {i}",
                parent_todo_id=current_todo.id if current_todo else None,
            )
            if i < 5:  # Create first 5 levels normally
                current_todo = await service.create_todo(todo_data, test_user.id)
            else:  # 6th level should fail
                with pytest.raises(MaxTodoDepthExceededError):
                    await service.create_todo(todo_data, test_user.id)

    @pytest.mark.asyncio
    async def test_create_todo_with_ai_subtasks(self, test_db, test_user):
        """Test todo creation with AI subtask generation."""
        service = TodoService(test_db)

        with patch.object(service, "_generate_ai_subtasks") as mock_ai:
            mock_ai.return_value = None

            todo_data = TodoCreate(title="AI Enhanced Todo", generate_ai_subtasks=True)

            result = await service.create_todo(todo_data, test_user.id, generate_ai_subtasks=True)

            assert result is not None
            mock_ai.assert_called_once_with(result)

    @pytest.mark.asyncio
    async def test_get_todo_by_id_success(self, test_db, test_user, test_todo):
        """Test getting todo by ID successfully."""
        service = TodoService(test_db)

        result = await service.get_todo_by_id(test_todo.id, test_user.id)

        assert result is not None
        assert result.id == test_todo.id
        assert result.user_id == test_user.id

    @pytest.mark.asyncio
    async def test_get_todo_by_id_nonexistent(self, test_db, test_user):
        """Test getting non-existent todo."""
        service = TodoService(test_db)
        fake_id = uuid.uuid4()

        result = await service.get_todo_by_id(fake_id, test_user.id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_todo_by_id_wrong_user(self, test_db, test_user_2, test_todo):
        """Test getting todo belonging to different user."""
        service = TodoService(test_db)

        result = await service.get_todo_by_id(test_todo.id, test_user_2.id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_todo_with_subtasks(self, test_db, test_user, test_todo_with_subtasks):
        """Test getting todo with its subtasks."""
        service = TodoService(test_db)

        result = await service.get_todo_with_subtasks(test_todo_with_subtasks.id, test_user.id)

        assert result is not None
        assert result.id == test_todo_with_subtasks.id
        assert len(result.subtasks) == 2

    @pytest.mark.asyncio
    async def test_get_todos_list_basic(self, test_db, test_user):
        """Test getting basic todos list."""
        service = TodoService(test_db)

        # Create some test todos
        for i in range(3):
            todo_data = TodoCreate(title=f"Todo {i}")
            await service.create_todo(todo_data, test_user.id)

        filters = TodoFilter()
        pagination = PaginationParams(page=1, size=10)

        result = await service.get_todos_list(test_user.id, filters, pagination)

        assert result["total"] == 3
        assert len(result["items"]) == 3
        assert result["page"] == 1
        assert result["has_next"] is False

    @pytest.mark.asyncio
    async def test_get_todos_list_with_status_filter(self, test_db, test_user):
        """Test todos list with status filter."""
        service = TodoService(test_db)

        # Create todos with different statuses
        for status in ["todo", "in_progress", "done"]:
            todo_data = TodoCreate(title=f"Todo {status}", status=status)
            await service.create_todo(todo_data, test_user.id)

        filters = TodoFilter(status="done")
        pagination = PaginationParams(page=1, size=10)

        result = await service.get_todos_list(test_user.id, filters, pagination)

        assert result["total"] == 1
        assert result["items"][0].status == "done"

    @pytest.mark.asyncio
    async def test_get_todos_list_with_priority_filter(self, test_db, test_user):
        """Test todos list with priority filter."""
        service = TodoService(test_db)

        # Create todos with different priorities
        for priority in [1, 3, 5]:
            todo_data = TodoCreate(title=f"Priority {priority}", priority=priority)
            await service.create_todo(todo_data, test_user.id)

        filters = TodoFilter(priority=5)
        pagination = PaginationParams(page=1, size=10)

        result = await service.get_todos_list(test_user.id, filters, pagination)

        assert result["total"] == 1
        assert result["items"][0].priority == 5

    @pytest.mark.asyncio
    async def test_get_todos_list_with_project_filter(self, test_db, test_user, test_project):
        """Test todos list with project filter."""
        service = TodoService(test_db)

        # Create todos with and without project
        todo_data_1 = TodoCreate(title="Project Todo", project_id=test_project.id)
        todo_data_2 = TodoCreate(title="No Project Todo")

        await service.create_todo(todo_data_1, test_user.id)
        await service.create_todo(todo_data_2, test_user.id)

        filters = TodoFilter(project_id=test_project.id)
        pagination = PaginationParams(page=1, size=10)

        result = await service.get_todos_list(test_user.id, filters, pagination)

        assert result["total"] == 1
        assert result["items"][0].project_id == test_project.id

    @pytest.mark.asyncio
    async def test_get_todos_list_with_search(self, test_db, test_user):
        """Test todos list with search filter."""
        service = TodoService(test_db)

        todo_data_1 = TodoCreate(title="Important Meeting", description="Discuss project progress")
        todo_data_2 = TodoCreate(title="Code Review", description="Review pull request")

        await service.create_todo(todo_data_1, test_user.id)
        await service.create_todo(todo_data_2, test_user.id)

        filters = TodoFilter(search="meeting")
        pagination = PaginationParams(page=1, size=10)

        result = await service.get_todos_list(test_user.id, filters, pagination)

        assert result["total"] == 1
        assert "Meeting" in result["items"][0].title

    @pytest.mark.asyncio
    async def test_update_todo_success(self, test_db, test_user, test_todo):
        """Test successful todo update."""
        service = TodoService(test_db)
        update_data = TodoUpdate(title="Updated Title", status="in_progress", priority=5)

        result = await service.update_todo(test_todo.id, update_data, test_user.id)

        assert result is not None
        assert result.title == "Updated Title"
        assert result.status == "in_progress"
        assert result.priority == 5

    @pytest.mark.asyncio
    async def test_update_todo_mark_completed(self, test_db, test_user, test_todo):
        """Test marking todo as completed sets completed_at."""
        service = TodoService(test_db)
        update_data = TodoUpdate(status="done")

        result = await service.update_todo(test_todo.id, update_data, test_user.id)

        assert result is not None
        assert result.status == "done"
        assert result.completed_at is not None

    @pytest.mark.asyncio
    async def test_update_todo_unmark_completed(self, test_db, test_user, completed_todo):
        """Test unmarking completed todo clears completed_at."""
        service = TodoService(test_db)
        update_data = TodoUpdate(status="todo")

        result = await service.update_todo(completed_todo.id, update_data, test_user.id)

        assert result is not None
        assert result.status == "todo"
        assert result.completed_at is None

    @pytest.mark.asyncio
    async def test_update_todo_nonexistent(self, test_db, test_user):
        """Test updating non-existent todo."""
        service = TodoService(test_db)
        fake_id = uuid.uuid4()
        update_data = TodoUpdate(title="Should fail")

        with pytest.raises(TodoNotFoundError):
            await service.update_todo(fake_id, update_data, test_user.id)

    @pytest.mark.asyncio
    async def test_delete_todo_success(self, test_db, test_user, test_todo):
        """Test successful todo deletion."""
        service = TodoService(test_db)
        todo_id = test_todo.id

        result = await service.delete_todo(todo_id, test_user.id)

        assert result is True

        # Verify todo is deleted
        deleted_todo = await service.get_todo_by_id(todo_id, test_user.id)
        assert deleted_todo is None

    @pytest.mark.asyncio
    async def test_delete_todo_with_subtasks(self, test_db, test_user, test_todo_with_subtasks):
        """Test deleting todo cascades to subtasks."""
        service = TodoService(test_db)
        parent_id = test_todo_with_subtasks.id
        subtask_ids = [subtask.id for subtask in test_todo_with_subtasks.subtasks]

        result = await service.delete_todo(parent_id, test_user.id)

        assert result is True

        # Verify parent and subtasks are deleted
        for subtask_id in subtask_ids:
            deleted_subtask = await service.get_todo_by_id(subtask_id, test_user.id)
            assert deleted_subtask is None

    @pytest.mark.asyncio
    async def test_delete_todo_nonexistent(self, test_db, test_user):
        """Test deleting non-existent todo."""
        service = TodoService(test_db)
        fake_id = uuid.uuid4()

        with pytest.raises(TodoNotFoundError):
            await service.delete_todo(fake_id, test_user.id)

    @pytest.mark.asyncio
    async def test_toggle_todo_status_to_done(self, test_db, test_user, test_todo):
        """Test toggling todo status from todo to done."""
        service = TodoService(test_db)

        result = await service.toggle_todo_status(test_todo.id, test_user.id)

        assert result is not None
        assert result.status == "done"
        assert result.completed_at is not None

    @pytest.mark.asyncio
    async def test_toggle_todo_status_to_todo(self, test_db, test_user, completed_todo):
        """Test toggling todo status from done to todo."""
        service = TodoService(test_db)

        result = await service.toggle_todo_status(completed_todo.id, test_user.id)

        assert result is not None
        assert result.status == "todo"
        assert result.completed_at is None

    @pytest.mark.asyncio
    async def test_toggle_todo_status_in_progress(self, test_db, test_user):
        """Test toggling in_progress todo status."""
        service = TodoService(test_db)
        todo_data = TodoCreate(title="In Progress Todo", status="in_progress")
        todo = await service.create_todo(todo_data, test_user.id)

        result = await service.toggle_todo_status(todo.id, test_user.id)

        assert result is not None
        assert result.status == "done"
        assert result.completed_at is not None

    @pytest.mark.asyncio
    async def test_get_user_todo_stats(self, test_db, test_user):
        """Test getting user todo statistics."""
        service = TodoService(test_db)

        # Create todos with different statuses
        todo_data_pending = TodoCreate(title="Pending Todo", status="todo")
        todo_data_progress = TodoCreate(title="In Progress Todo", status="in_progress")
        todo_data_done = TodoCreate(title="Done Todo", status="done")
        todo_data_overdue = TodoCreate(
            title="Overdue Todo",
            status="todo",
            due_date=datetime.now(timezone.utc) - timedelta(days=1),
        )

        await service.create_todo(todo_data_pending, test_user.id)
        await service.create_todo(todo_data_progress, test_user.id)
        await service.create_todo(todo_data_done, test_user.id)
        await service.create_todo(todo_data_overdue, test_user.id)

        stats = await service.get_user_todo_stats(test_user.id)

        assert stats["total_todos"] == 4
        assert stats["completed_todos"] == 1
        assert stats["in_progress_todos"] == 1
        assert stats["pending_todos"] == 2
        assert stats["overdue_todos"] == 1
        assert stats["completion_rate"] == 25.0  # 1/4 * 100

    @pytest.mark.asyncio
    async def test_get_user_todo_stats_no_todos(self, test_db, test_user):
        """Test todo stats for user with no todos."""
        service = TodoService(test_db)

        stats = await service.get_user_todo_stats(test_user.id)

        assert stats["total_todos"] == 0
        assert stats["completed_todos"] == 0
        assert stats["in_progress_todos"] == 0
        assert stats["pending_todos"] == 0
        assert stats["overdue_todos"] == 0
        assert stats["completion_rate"] == 0

    @pytest.mark.asyncio
    async def test_normalize_datetime_timezone_naive(self, test_db):
        """Test datetime normalization for timezone-naive datetime."""
        service = TodoService(test_db)
        naive_dt = datetime(2023, 12, 25, 15, 30, 0)

        result = service._normalize_datetime(naive_dt)

        assert result.tzinfo == timezone.utc
        assert result.year == 2023
        assert result.month == 12
        assert result.day == 25

    @pytest.mark.asyncio
    async def test_normalize_datetime_timezone_aware(self, test_db):
        """Test datetime normalization for timezone-aware datetime."""
        service = TodoService(test_db)
        aware_dt = datetime(2023, 12, 25, 15, 30, 0, tzinfo=timezone.utc)

        result = service._normalize_datetime(aware_dt)

        assert result.tzinfo == timezone.utc
        assert result == aware_dt

    @pytest.mark.asyncio
    async def test_normalize_datetime_none(self, test_db):
        """Test datetime normalization for None value."""
        service = TodoService(test_db)

        result = service._normalize_datetime(None)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_todo_depth_no_parent(self, test_db, test_user):
        """Test getting depth for todo without parent."""
        service = TodoService(test_db)
        todo_data = TodoCreate(title="Root Todo")
        todo = await service.create_todo(todo_data, test_user.id)

        depth = await service._get_todo_depth(todo)

        assert depth == 0

    @pytest.mark.asyncio
    async def test_get_todo_depth_with_parent(self, test_db, test_user, test_todo):
        """Test getting depth for todo with parent."""
        service = TodoService(test_db)
        subtask_data = TodoCreate(title="Subtask", parent_todo_id=test_todo.id)
        subtask = await service.create_todo(subtask_data, test_user.id)

        depth = await service._get_todo_depth(subtask)

        assert depth == 1

    @pytest.mark.asyncio
    async def test_validate_project_ownership_success(self, test_db, test_user, test_project):
        """Test project ownership validation success."""
        service = TodoService(test_db)

        # Should not raise an exception
        await service._validate_project_ownership(test_project.id, test_user.id)

    @pytest.mark.asyncio
    async def test_validate_project_ownership_failure(self, test_db, test_user_2, test_project):
        """Test project ownership validation failure."""
        service = TodoService(test_db)

        with pytest.raises(TodoPermissionError):
            await service._validate_project_ownership(test_project.id, test_user_2.id)

    @pytest.mark.asyncio
    async def test_validate_project_ownership_none(self, test_db, test_user):
        """Test project ownership validation with None project_id."""
        service = TodoService(test_db)

        # Should not raise an exception
        await service._validate_project_ownership(None, test_user.id)
