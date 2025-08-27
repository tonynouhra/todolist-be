"""
Unit tests for ProjectService.

This module contains comprehensive unit tests for the ProjectService class,
testing all business logic methods including project management and todo relationships.
"""

import uuid
from unittest.mock import patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.domains.project.service import ProjectService
from app.exceptions.base import NotFoundError, ValidationError
from app.schemas.project import ProjectCreate, ProjectFilter, ProjectUpdate
from app.shared.pagination import PaginationParams


class TestProjectService:
    """Test cases for ProjectService."""

    @pytest.mark.asyncio
    async def test_create_project_success(self, test_db, test_user):
        """Test successful project creation."""
        service = ProjectService(test_db)
        project_data = ProjectCreate(name="New Project", description="A new test project")

        result = await service.create_project(project_data, test_user.id)

        assert result is not None
        assert result.name == "New Project"
        assert result.description == "A new test project"
        assert result.user_id == test_user.id

    @pytest.mark.asyncio
    async def test_create_project_minimal_data(self, test_db, test_user):
        """Test project creation with minimal data."""
        service = ProjectService(test_db)
        project_data = ProjectCreate(name="Minimal Project")

        result = await service.create_project(project_data, test_user.id)

        assert result is not None
        assert result.name == "Minimal Project"
        assert result.description is None
        assert result.user_id == test_user.id

    @pytest.mark.asyncio
    async def test_create_project_duplicate_name(self, test_db, test_user, test_project):
        """Test creating project with duplicate name for same user."""
        service = ProjectService(test_db)
        project_data = ProjectCreate(
            name=test_project.name,  # Same name as existing project
            description="Duplicate name",
        )

        with pytest.raises(ValidationError, match="A project with this name already exists"):
            await service.create_project(project_data, test_user.id)

    @pytest.mark.asyncio
    async def test_create_project_same_name_different_user(
        self, test_db, test_user, test_user_2, test_project
    ):
        """Test creating project with same name but different user."""
        service = ProjectService(test_db)
        project_data = ProjectCreate(
            name=test_project.name,  # Same name as test_user's project
            description="Different user project",
        )

        result = await service.create_project(project_data, test_user_2.id)

        assert result is not None
        assert result.name == test_project.name
        assert result.user_id == test_user_2.id

    @pytest.mark.asyncio
    async def test_get_project_by_id_success(self, test_db, test_user, test_project):
        """Test getting project by ID successfully."""
        service = ProjectService(test_db)

        result = await service.get_project_by_id(test_project.id, test_user.id)

        assert result is not None
        assert result.id == test_project.id
        assert result.user_id == test_user.id

    @pytest.mark.asyncio
    async def test_get_project_by_id_nonexistent(self, test_db, test_user):
        """Test getting non-existent project."""
        service = ProjectService(test_db)
        fake_id = uuid.uuid4()

        result = await service.get_project_by_id(fake_id, test_user.id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_project_by_id_wrong_user(self, test_db, test_user_2, test_project):
        """Test getting project belonging to different user."""
        service = ProjectService(test_db)

        result = await service.get_project_by_id(test_project.id, test_user_2.id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_project_with_todos(self, test_db, test_user, test_project, test_todo):
        """Test getting project with its todos."""
        service = ProjectService(test_db)

        result = await service.get_project_with_todos(test_project.id, test_user.id)

        assert result is not None
        assert result.id == test_project.id
        assert len(result.todos) == 1
        assert result.todos[0].id == test_todo.id

    @pytest.mark.asyncio
    async def test_get_projects_list_basic(self, test_db, test_user):
        """Test getting basic projects list."""
        service = ProjectService(test_db)

        # Create test projects
        for i in range(3):
            project_data = ProjectCreate(name=f"Project {i}")
            await service.create_project(project_data, test_user.id)

        filters = ProjectFilter()
        pagination = PaginationParams(page=1, size=10)

        result = await service.get_projects_list(test_user.id, filters, pagination)

        assert result["total"] == 3
        assert len(result["items"]) == 3
        assert result["page"] == 1
        assert result["has_next"] is False

    @pytest.mark.asyncio
    async def test_get_projects_list_with_search_name(self, test_db, test_user):
        """Test projects list with name search."""
        service = ProjectService(test_db)

        project_data_1 = ProjectCreate(name="Important Project")
        project_data_2 = ProjectCreate(name="Regular Project")

        await service.create_project(project_data_1, test_user.id)
        await service.create_project(project_data_2, test_user.id)

        filters = ProjectFilter(search="important")
        pagination = PaginationParams(page=1, size=10)

        result = await service.get_projects_list(test_user.id, filters, pagination)

        assert result["total"] == 1
        assert "Important" in result["items"][0].name

    @pytest.mark.asyncio
    async def test_get_projects_list_with_search_description(self, test_db, test_user):
        """Test projects list with description search."""
        service = ProjectService(test_db)

        project_data_1 = ProjectCreate(
            name="Project One", description="This contains special keyword"
        )
        project_data_2 = ProjectCreate(name="Project Two", description="Regular description")

        await service.create_project(project_data_1, test_user.id)
        await service.create_project(project_data_2, test_user.id)

        filters = ProjectFilter(search="special")
        pagination = PaginationParams(page=1, size=10)

        result = await service.get_projects_list(test_user.id, filters, pagination)

        assert result["total"] == 1
        assert result["items"][0].name == "Project One"

    @pytest.mark.asyncio
    async def test_get_projects_list_no_pagination(self, test_db, test_user):
        """Test getting projects list without pagination."""
        service = ProjectService(test_db)

        # Create test projects
        for i in range(2):
            project_data = ProjectCreate(name=f"Project {i}")
            await service.create_project(project_data, test_user.id)

        result = await service.get_projects_list(test_user.id)

        assert result["total"] == 2
        assert len(result["items"]) == 2
        assert result["page"] == 1
        assert result["has_next"] is False

    @pytest.mark.asyncio
    async def test_update_project_success(self, test_db, test_user, test_project):
        """Test successful project update."""
        service = ProjectService(test_db)
        update_data = ProjectUpdate(name="Updated Project Name", description="Updated description")

        result = await service.update_project(test_project.id, update_data, test_user.id)

        assert result is not None
        assert result.name == "Updated Project Name"
        assert result.description == "Updated description"
        assert result.id == test_project.id

    @pytest.mark.asyncio
    async def test_update_project_partial(self, test_db, test_user, test_project):
        """Test partial project update."""
        service = ProjectService(test_db)
        original_description = test_project.description
        update_data = ProjectUpdate(name="New Name Only")

        result = await service.update_project(test_project.id, update_data, test_user.id)

        assert result is not None
        assert result.name == "New Name Only"
        assert result.description == original_description

    @pytest.mark.asyncio
    async def test_update_project_nonexistent(self, test_db, test_user):
        """Test updating non-existent project."""
        service = ProjectService(test_db)
        fake_id = uuid.uuid4()
        update_data = ProjectUpdate(name="Should Fail")

        with pytest.raises(NotFoundError):
            await service.update_project(fake_id, update_data, test_user.id)

    @pytest.mark.asyncio
    async def test_update_project_duplicate_name(
        self, test_db, test_user, test_project, test_project_2
    ):
        """Test updating project to duplicate name."""
        service = ProjectService(test_db)
        update_data = ProjectUpdate(name=test_project_2.name)

        with pytest.raises(ValidationError, match="A project with this name already exists"):
            await service.update_project(test_project.id, update_data, test_user.id)

    @pytest.mark.asyncio
    async def test_update_project_same_name(self, test_db, test_user, test_project):
        """Test updating project with same name (should succeed)."""
        service = ProjectService(test_db)
        update_data = ProjectUpdate(
            name=test_project.name, description="Updated description only"  # Same name
        )

        result = await service.update_project(test_project.id, update_data, test_user.id)

        assert result is not None
        assert result.name == test_project.name
        assert result.description == "Updated description only"

    @pytest.mark.asyncio
    async def test_delete_project_success(self, test_db, test_user, test_project):
        """Test successful project deletion."""
        service = ProjectService(test_db)
        project_id = test_project.id

        result = await service.delete_project(project_id, test_user.id)

        assert result is True

        # Verify project is deleted
        deleted_project = await service.get_project_by_id(project_id, test_user.id)
        assert deleted_project is None

    @pytest.mark.asyncio
    async def test_delete_project_with_todos_unassign(
        self, test_db, test_user, test_project, test_todo
    ):
        """Test deleting project with todos unassigns them."""
        service = ProjectService(test_db)
        project_id = test_project.id
        todo_id = test_todo.id

        # Verify todo is assigned to project
        assert test_todo.project_id == project_id

        result = await service.delete_project(project_id, test_user.id)

        assert result is True

        # Verify project is deleted
        deleted_project = await service.get_project_by_id(project_id, test_user.id)
        assert deleted_project is None

        # Verify todo still exists but is unassigned from project
        from app.domains.todo.service import TodoService

        todo_service = TodoService(test_db)
        updated_todo = await todo_service.get_todo_by_id(todo_id, test_user.id)
        assert updated_todo is not None
        assert updated_todo.project_id is None

    @pytest.mark.asyncio
    async def test_delete_project_nonexistent(self, test_db, test_user):
        """Test deleting non-existent project."""
        service = ProjectService(test_db)
        fake_id = uuid.uuid4()

        with pytest.raises(NotFoundError):
            await service.delete_project(fake_id, test_user.id)

    @pytest.mark.asyncio
    async def test_get_project_stats(self, test_db, test_user):
        """Test getting project statistics."""
        service = ProjectService(test_db)

        # Create projects with and without todos
        project1_data = ProjectCreate(name="Project with todos")
        project1 = await service.create_project(project1_data, test_user.id)

        project2_data = ProjectCreate(name="Empty project")
        await service.create_project(project2_data, test_user.id)

        # Create todos for project1
        from app.domains.todo.service import TodoService
        from app.schemas.todo import TodoCreate

        todo_service = TodoService(test_db)
        for i in range(3):
            todo_data = TodoCreate(title=f"Todo {i}", project_id=project1.id)
            await todo_service.create_todo(todo_data, test_user.id)

        stats = await service.get_project_stats(test_user.id)

        assert stats["total_projects"] == 2
        assert stats["projects_with_todos"] == 1
        assert stats["average_todos_per_project"] == 1.5  # (3 + 0) / 2

    @pytest.mark.asyncio
    async def test_get_project_stats_no_projects(self, test_db, test_user):
        """Test project stats for user with no projects."""
        service = ProjectService(test_db)

        stats = await service.get_project_stats(test_user.id)

        assert stats["total_projects"] == 0
        assert stats["projects_with_todos"] == 0
        assert stats["average_todos_per_project"] == 0.0

    @pytest.mark.asyncio
    async def test_get_project_with_todo_counts(self, test_db, test_user, test_project):
        """Test getting project with todo counts."""
        service = ProjectService(test_db)

        # Create todos with different statuses
        from app.domains.todo.service import TodoService
        from app.schemas.todo import TodoCreate

        todo_service = TodoService(test_db)

        # Create todos: 2 regular, 1 completed
        todo_data_1 = TodoCreate(title="Todo 1", project_id=test_project.id, status="todo")
        todo_data_2 = TodoCreate(title="Todo 2", project_id=test_project.id, status="in_progress")
        todo_data_3 = TodoCreate(title="Todo 3", project_id=test_project.id, status="done")

        await todo_service.create_todo(todo_data_1, test_user.id)
        await todo_service.create_todo(todo_data_2, test_user.id)
        await todo_service.create_todo(todo_data_3, test_user.id)

        result = await service.get_project_with_todo_counts(test_project.id, test_user.id)

        assert result is not None
        assert result["id"] == test_project.id
        assert result["name"] == test_project.name
        assert result["todo_count"] == 3
        assert result["completed_todo_count"] == 1

    @pytest.mark.asyncio
    async def test_get_project_with_todo_counts_nonexistent(self, test_db, test_user):
        """Test getting todo counts for non-existent project."""
        service = ProjectService(test_db)
        fake_id = uuid.uuid4()

        result = await service.get_project_with_todo_counts(fake_id, test_user.id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_project_with_todo_counts_no_todos(self, test_db, test_user, test_project):
        """Test getting todo counts for project with no todos."""
        service = ProjectService(test_db)

        result = await service.get_project_with_todo_counts(test_project.id, test_user.id)

        assert result is not None
        assert result["todo_count"] == 0
        assert result["completed_todo_count"] == 0

    @pytest.mark.asyncio
    async def test_unassign_todos_from_project(self, test_db, test_user, test_project, test_todo):
        """Test unassigning todos from project."""
        service = ProjectService(test_db)

        # Verify todo is assigned
        assert test_todo.project_id == test_project.id

        await service._unassign_todos_from_project(test_project.id)
        await test_db.commit()

        # Refresh todo and check it's unassigned
        await test_db.refresh(test_todo)
        assert test_todo.project_id is None

    @pytest.mark.asyncio
    async def test_get_project_todo_count(self, test_db, test_user, test_project):
        """Test getting todo count for project."""
        service = ProjectService(test_db)

        # Create multiple todos
        from app.domains.todo.service import TodoService
        from app.schemas.todo import TodoCreate

        todo_service = TodoService(test_db)
        for i in range(5):
            todo_data = TodoCreate(title=f"Todo {i}", project_id=test_project.id)
            await todo_service.create_todo(todo_data, test_user.id)

        count = await service._get_project_todo_count(test_project.id)

        assert count == 5

    @pytest.mark.asyncio
    async def test_get_project_by_name_and_user(self, test_db, test_user, test_project):
        """Test getting project by name and user."""
        service = ProjectService(test_db)

        result = await service._get_project_by_name_and_user(test_project.name, test_user.id)

        assert result is not None
        assert result.id == test_project.id

    @pytest.mark.asyncio
    async def test_get_project_by_name_and_user_different_user(
        self, test_db, test_user_2, test_project
    ):
        """Test getting project by name with different user."""
        service = ProjectService(test_db)

        result = await service._get_project_by_name_and_user(test_project.name, test_user_2.id)

        assert result is None

    @pytest.mark.asyncio
    async def test_create_project_database_error(self, test_db, test_user):
        """Test project creation with database error."""
        service = ProjectService(test_db)

        with patch.object(test_db, "commit", side_effect=SQLAlchemyError("Database error")):
            with patch.object(test_db, "rollback") as mock_rollback:
                with pytest.raises(ValidationError):
                    project_data = ProjectCreate(name="Error Project")
                    await service.create_project(project_data, test_user.id)
                mock_rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_project_database_error(self, test_db, test_user, test_project):
        """Test project update with database error."""
        service = ProjectService(test_db)

        with patch.object(test_db, "commit", side_effect=SQLAlchemyError("Database error")):
            with patch.object(test_db, "rollback") as mock_rollback:
                with pytest.raises(ValidationError):
                    update_data = ProjectUpdate(name="Error Update")
                    await service.update_project(test_project.id, update_data, test_user.id)
                mock_rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_project_database_error(self, test_db, test_user, test_project):
        """Test project deletion with database error."""
        service = ProjectService(test_db)

        with patch.object(test_db, "commit", side_effect=SQLAlchemyError("Database error")):
            with patch.object(test_db, "rollback") as mock_rollback:
                with pytest.raises(ValidationError):
                    await service.delete_project(test_project.id, test_user.id)
                mock_rollback.assert_called_once()
