"""
Service integration tests.

This module contains integration tests that verify how different services
work together, testing cross-service interactions and workflows.
"""

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from app.domains.project.service import ProjectService
from app.domains.todo.service import TodoService
from app.domains.user.service import UserService
from app.schemas.ai import GeneratedSubtask, SubtaskGenerationResponse
from app.schemas.project import ProjectCreate
from app.schemas.todo import TodoCreate, TodoUpdate


class TestServiceIntegration:
    """Integration tests for service interactions."""

    @pytest.mark.asyncio
    async def test_user_project_todo_workflow(self, test_db):
        """Test complete user-project-todo workflow."""
        user_service = UserService(test_db)
        project_service = ProjectService(test_db)
        todo_service = TodoService(test_db)

        # Create user
        user = await user_service.create_user(
            clerk_user_id=f"clerk_user_{uuid.uuid4()}",
            email="workflow@example.com",
            username="workflowuser",
        )

        # Create project for user
        project_data = ProjectCreate(
            name="Workflow Project", description="Testing complete workflow"
        )
        project = await project_service.create_project(project_data, user.id)

        # Create todos in project
        todo_data = TodoCreate(
            title="Workflow Todo",
            description="Part of the workflow test",
            project_id=project.id,
            priority=4,
            due_date=datetime.now(UTC) + timedelta(days=5),
        )
        todo = await todo_service.create_todo(todo_data, user.id)

        # Verify relationships
        assert todo.user_id == user.id
        assert todo.project_id == project.id

        # Get project with todos
        project_with_todos = await project_service.get_project_with_todos(project.id, user.id)
        assert len(project_with_todos.todos) == 1
        assert project_with_todos.todos[0].id == todo.id

        # Update todo status
        update_data = TodoUpdate(status="done")
        updated_todo = await todo_service.update_todo(todo.id, update_data, user.id)
        assert updated_todo.status == "done"
        assert updated_todo.completed_at is not None

        # Get project stats
        project_stats = await project_service.get_project_stats(user.id)
        assert project_stats["total_projects"] >= 1
        assert project_stats["projects_with_todos"] >= 1

        # Get user todo stats
        user_stats = await todo_service.get_user_todo_stats(user.id)
        assert user_stats["total_todos"] >= 1
        assert user_stats["completed_todos"] >= 1

    @pytest.mark.asyncio
    async def test_hierarchical_todo_creation_workflow(self, test_db, test_user):
        """Test creating hierarchical todos across services."""
        project_service = ProjectService(test_db)
        todo_service = TodoService(test_db)

        # Create project
        project_data = ProjectCreate(name="Hierarchical Project")
        project = await project_service.create_project(project_data, test_user.id)

        # Create parent todo
        parent_data = TodoCreate(
            title="Complex Project Task",
            description="This task will have subtasks",
            project_id=project.id,
            priority=5,
            status="in_progress",
        )
        parent_todo = await todo_service.create_todo(parent_data, test_user.id)

        # Create subtasks
        subtasks = []
        subtask_titles = [
            "Research phase",
            "Design phase",
            "Implementation phase",
            "Testing phase",
        ]

        for i, title in enumerate(subtask_titles):
            subtask_data = TodoCreate(
                title=title,
                parent_todo_id=parent_todo.id,
                project_id=project.id,
                priority=4 - i,  # Decreasing priority
                status="todo",
            )
            subtask = await todo_service.create_todo(subtask_data, test_user.id)
            subtasks.append(subtask)

        # Verify hierarchy
        parent_with_subtasks = await todo_service.get_todo_with_subtasks(
            parent_todo.id, test_user.id
        )
        assert len(parent_with_subtasks.subtasks) == 4

        # Verify all subtasks belong to same project
        for subtask in parent_with_subtasks.subtasks:
            assert subtask.project_id == project.id
            assert subtask.parent_todo_id == parent_todo.id

        # Complete subtasks one by one
        for subtask in subtasks[:2]:  # Complete first 2
            update_data = TodoUpdate(status="done")
            await todo_service.update_todo(subtask.id, update_data, test_user.id)

        # Get updated project statistics
        project_with_counts = await project_service.get_project_with_todo_counts(
            project.id, test_user.id
        )

        assert project_with_counts["todo_count"] == 5  # 1 parent + 4 subtasks
        assert project_with_counts["completed_todo_count"] == 2

    @pytest.mark.asyncio
    async def test_ai_subtask_generation_integration(self, test_db, test_user):
        """Test AI subtask generation integration with todo service."""
        todo_service = TodoService(test_db)

        # Create parent todo
        parent_data = TodoCreate(
            title="Plan company retreat",
            description="Organize a 3-day company retreat for the team",
            priority=5,
        )
        parent_todo = await todo_service.create_todo(parent_data, test_user.id)

        # Mock AI service response
        mock_subtasks = [
            GeneratedSubtask(
                title="Book venue and accommodation",
                description="Find and book a suitable location",
                priority=5,
                estimated_time="4 hours",
                order=1,
            ),
            GeneratedSubtask(
                title="Plan activities and workshops",
                description="Design team building activities",
                priority=4,
                estimated_time="6 hours",
                order=2,
            ),
            GeneratedSubtask(
                title="Arrange catering and meals",
                description="Coordinate food for all participants",
                priority=4,
                estimated_time="3 hours",
                order=3,
            ),
        ]

        mock_response = SubtaskGenerationResponse(
            parent_task_title=parent_todo.title,
            generated_subtasks=mock_subtasks,
            total_subtasks=len(mock_subtasks),
            generation_timestamp=datetime.now(UTC),
            ai_model="gemini-pro",
        )

        with patch(
            "app.domains.ai.service.AIService.generate_subtasks",
            return_value=mock_response,
        ), patch.object(todo_service, "_generate_ai_subtasks") as mock_generate:
            # Simulate the AI subtask generation process
            async def create_subtasks(todo):
                for subtask_data in mock_subtasks:
                    subtask_create = TodoCreate(
                        title=subtask_data.title,
                        description=subtask_data.description,
                        priority=subtask_data.priority,
                        parent_todo_id=todo.id,
                        ai_generated=True,
                        status="todo",
                    )
                    await todo_service.create_todo(subtask_create, test_user.id)

            mock_generate.side_effect = create_subtasks

            # Create todo with AI subtasks
            ai_todo_data = TodoCreate(
                title="AI Enhanced Task",
                description="This will generate AI subtasks",
                generate_ai_subtasks=True,
            )

            ai_todo = await todo_service.create_todo(
                ai_todo_data, test_user.id, generate_ai_subtasks=True
            )

            # Verify subtasks were created
            todo_with_subtasks = await todo_service.get_todo_with_subtasks(ai_todo.id, test_user.id)

            assert len(todo_with_subtasks.subtasks) == 3
            for subtask in todo_with_subtasks.subtasks:
                assert subtask.ai_generated is True
                assert subtask.parent_todo_id == ai_todo.id

    @pytest.mark.asyncio
    async def test_project_deletion_impact_on_todos(self, test_db, test_user):
        """Test how project deletion affects related todos."""
        project_service = ProjectService(test_db)
        todo_service = TodoService(test_db)

        # Create project
        project_data = ProjectCreate(
            name="Deletion Test Project", description="Will be deleted to test impact"
        )
        project = await project_service.create_project(project_data, test_user.id)

        # Create todos in the project
        todo_ids = []
        for i in range(5):
            todo_data = TodoCreate(
                title=f"Project Todo {i}",
                project_id=project.id,
                status="todo" if i % 2 == 0 else "done",
            )
            todo = await todo_service.create_todo(todo_data, test_user.id)
            todo_ids.append(todo.id)

        # Create some todos NOT in the project
        other_todo_data = TodoCreate(title="Independent Todo")
        other_todo = await todo_service.create_todo(other_todo_data, test_user.id)

        # Delete project
        success = await project_service.delete_project(project.id, test_user.id)
        assert success is True

        # Verify todos are unassigned from project (not deleted)
        for todo_id in todo_ids:
            todo = await todo_service.get_todo_by_id(todo_id, test_user.id)
            assert todo is not None  # Todo still exists
            assert todo.project_id is None  # But unassigned from project

        # Verify independent todo is unaffected
        independent_todo = await todo_service.get_todo_by_id(other_todo.id, test_user.id)
        assert independent_todo is not None
        assert independent_todo.project_id is None  # Was already None

    @pytest.mark.asyncio
    async def test_user_deletion_cascade_across_services(self, test_db):
        """Test user deletion cascades across all services."""
        user_service = UserService(test_db)
        project_service = ProjectService(test_db)
        todo_service = TodoService(test_db)

        # Create user
        user = await user_service.create_user(
            clerk_user_id=f"clerk_user_{uuid.uuid4()}",
            email="cascade@example.com",
            username="cascadeuser",
        )

        # Create complete data structure
        project_data = ProjectCreate(name="User's Project")
        project = await project_service.create_project(project_data, user.id)

        parent_todo_data = TodoCreate(title="Parent Todo", project_id=project.id)
        parent_todo = await todo_service.create_todo(parent_todo_data, user.id)

        subtask_data = TodoCreate(
            title="Subtask", parent_todo_id=parent_todo.id, project_id=project.id
        )
        subtask = await todo_service.create_todo(subtask_data, user.id)

        # Store IDs for verification
        user_id = user.id
        project_id = project.id
        parent_todo_id = parent_todo.id
        subtask_id = subtask.id

        # Delete user
        success = await user_service.delete_user(user_id)
        assert success is True

        # Verify cascade deletion
        deleted_user = await user_service.get_user_by_id(user_id)
        deleted_project = await project_service.get_project_by_id(project_id, user_id)
        deleted_parent = await todo_service.get_todo_by_id(parent_todo_id, user_id)
        deleted_subtask = await todo_service.get_todo_by_id(subtask_id, user_id)

        assert deleted_user is None
        assert deleted_project is None
        assert deleted_parent is None
        assert deleted_subtask is None

    @pytest.mark.asyncio
    async def test_cross_service_statistics_integration(self, test_db, test_user):
        """Test statistics consistency across services."""
        project_service = ProjectService(test_db)
        todo_service = TodoService(test_db)

        # Create multiple projects with todos
        projects = []
        total_todos_created = 0
        total_completed = 0

        for i in range(3):
            project_data = ProjectCreate(name=f"Stats Project {i}")
            project = await project_service.create_project(project_data, test_user.id)
            projects.append(project)

            # Create todos with mixed statuses
            for j in range(4):
                status = "done" if j < 2 else "todo"  # First 2 are completed
                todo_data = TodoCreate(
                    title=f"Project {i} Todo {j}", project_id=project.id, status=status
                )
                await todo_service.create_todo(todo_data, test_user.id)
                total_todos_created += 1
                if status == "done":
                    total_completed += 1

        # Get project statistics
        project_stats = await project_service.get_project_stats(test_user.id)

        assert project_stats["total_projects"] == 3
        assert project_stats["projects_with_todos"] == 3
        assert project_stats["average_todos_per_project"] == 4.0

        # Get user todo statistics
        user_stats = await todo_service.get_user_todo_stats(test_user.id)

        assert user_stats["total_todos"] == total_todos_created
        assert user_stats["completed_todos"] == total_completed
        expected_completion_rate = (total_completed / total_todos_created) * 100
        assert user_stats["completion_rate"] == expected_completion_rate

    @pytest.mark.asyncio
    async def test_todo_update_affects_project_statistics(self, test_db, test_user):
        """Test that todo updates properly affect project statistics."""
        project_service = ProjectService(test_db)
        todo_service = TodoService(test_db)

        # Create project
        project_data = ProjectCreate(name="Dynamic Stats Project")
        project = await project_service.create_project(project_data, test_user.id)

        # Create todos
        todo_ids = []
        for i in range(5):
            todo_data = TodoCreate(title=f"Dynamic Todo {i}", project_id=project.id, status="todo")
            todo = await todo_service.create_todo(todo_data, test_user.id)
            todo_ids.append(todo.id)

        # Initial statistics
        initial_stats = await project_service.get_project_with_todo_counts(project.id, test_user.id)
        assert initial_stats["todo_count"] == 5
        assert initial_stats["completed_todo_count"] == 0

        # Complete some todos
        for todo_id in todo_ids[:3]:  # Complete first 3
            update_data = TodoUpdate(status="done")
            await todo_service.update_todo(todo_id, update_data, test_user.id)

        # Updated statistics
        updated_stats = await project_service.get_project_with_todo_counts(project.id, test_user.id)
        assert updated_stats["todo_count"] == 5  # Total count unchanged
        assert updated_stats["completed_todo_count"] == 3  # 3 completed

        # Complete remaining todos
        for todo_id in todo_ids[3:]:
            update_data = TodoUpdate(status="done")
            await todo_service.update_todo(todo_id, update_data, test_user.id)

        # Final statistics
        final_stats = await project_service.get_project_with_todo_counts(project.id, test_user.id)
        assert final_stats["todo_count"] == 5
        assert final_stats["completed_todo_count"] == 5

    @pytest.mark.asyncio
    async def test_service_error_handling_integration(self, test_db, test_user):
        """Test error handling across service interactions."""
        ProjectService(test_db)
        todo_service = TodoService(test_db)

        # Test creating todo with non-existent project
        fake_project_id = uuid.uuid4()
        todo_data = TodoCreate(title="Invalid Project Todo", project_id=fake_project_id)

        from app.exceptions.todo import InvalidTodoOperationError

        with pytest.raises(InvalidTodoOperationError):
            await todo_service.create_todo(todo_data, test_user.id)

        # Test creating subtask with non-existent parent
        fake_parent_id = uuid.uuid4()
        subtask_data = TodoCreate(title="Orphan Subtask", parent_todo_id=fake_parent_id)

        from app.exceptions.todo import TodoNotFoundError

        with pytest.raises(TodoNotFoundError):
            await todo_service.create_todo(subtask_data, test_user.id)

    @pytest.mark.asyncio
    async def test_concurrent_operations_integration(self, test_db, test_user):
        """Test multiple operations across services with shared session."""

        project_service = ProjectService(test_db)
        todo_service = TodoService(test_db)

        # Create project
        project_data = ProjectCreate(name="Concurrent Test Project")
        project = await project_service.create_project(project_data, test_user.id)

        # Concurrent todo creation
        async def create_todo(index):
            todo_data = TodoCreate(
                title=f"Concurrent Todo {index}",
                project_id=project.id,
                priority=index % 5 + 1,
            )
            return await todo_service.create_todo(todo_data, test_user.id)

        # Create 10 todos (using sequential execution to avoid session conflicts)
        todos = []
        for i in range(10):
            todo = await create_todo(i)
            todos.append(todo)

        assert len(todos) == 10
        assert all(todo.project_id == project.id for todo in todos)

        # Concurrent status updates
        async def update_todo_status(todo, status):
            update_data = TodoUpdate(status=status)
            return await todo_service.update_todo(todo.id, update_data, test_user.id)

        # Update half to "done" (sequential to avoid session conflicts)
        updated_todos = []
        for todo in todos[:5]:
            updated_todo = await update_todo_status(todo, "done")
            updated_todos.append(updated_todo)

        assert all(todo.status == "done" for todo in updated_todos)

        # Verify final project statistics
        final_stats = await project_service.get_project_with_todo_counts(project.id, test_user.id)
        assert final_stats["todo_count"] == 10
        assert final_stats["completed_todo_count"] == 5
