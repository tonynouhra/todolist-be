"""
Database integration tests.

This module contains integration tests that verify database operations,
model relationships, constraints, and data persistence across the application.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.domains.project.service import ProjectService
from app.domains.todo.service import TodoService
from app.domains.user.service import UserService
from models import AITodoInteraction, Project, Todo, User


class TestDatabaseIntegration:
    """Integration tests for database operations."""

    @pytest.mark.asyncio
    async def test_user_creation_and_retrieval(self, test_db):
        """Test user creation and retrieval operations."""
        user_service = UserService(test_db)

        # Create user
        clerk_id = f"clerk_user_{uuid.uuid4()}"
        user = await user_service.create_user(
            clerk_user_id=clerk_id,
            email="integration@example.com",
            username="integrationuser",
        )

        assert user.id is not None
        assert user.created_at is not None
        assert user.updated_at is not None

        # Retrieve user by different methods
        user_by_clerk_id = await user_service.get_user_by_clerk_id(clerk_id)
        user_by_id = await user_service.get_user_by_id(user.id)

        assert user_by_clerk_id.id == user.id
        assert user_by_id.id == user.id

    @pytest.mark.asyncio
    async def test_user_email_uniqueness_constraint(self, test_db):
        """Test that email uniqueness is enforced at database level."""
        user1 = User(
            clerk_user_id=f"clerk_user_{uuid.uuid4()}",
            email="unique@example.com",
            username="user1",
        )

        user2 = User(
            clerk_user_id=f"clerk_user_{uuid.uuid4()}",
            email="unique@example.com",  # Same email
            username="user2",
        )

        test_db.add(user1)
        await test_db.commit()

        test_db.add(user2)
        with pytest.raises(IntegrityError):
            await test_db.commit()

    @pytest.mark.asyncio
    async def test_user_clerk_id_uniqueness_constraint(self, test_db):
        """Test that Clerk user ID uniqueness is enforced."""
        clerk_id = f"clerk_user_{uuid.uuid4()}"

        user1 = User(clerk_user_id=clerk_id, email="user1@example.com", username="user1")

        user2 = User(
            clerk_user_id=clerk_id,  # Same clerk_user_id
            email="user2@example.com",
            username="user2",
        )

        test_db.add(user1)
        await test_db.commit()

        test_db.add(user2)
        with pytest.raises(IntegrityError):
            await test_db.commit()

    @pytest.mark.asyncio
    async def test_todo_project_relationship(self, test_db, test_user):
        """Test todo-project relationship integrity."""
        # Create project
        project = Project(
            user_id=test_user.id,
            name="Integration Test Project",
            description="For testing relationships",
        )
        test_db.add(project)
        await test_db.commit()
        await test_db.refresh(project)

        # Create todos associated with project
        todos = []
        for i in range(3):
            todo = Todo(
                user_id=test_user.id,
                project_id=project.id,
                title=f"Project Todo {i}",
                status="todo",
                priority=i + 1,
            )
            todos.append(todo)
            test_db.add(todo)

        await test_db.commit()

        # Test relationship queries
        stmt = select(Project).where(Project.id == project.id).options(selectinload(Project.todos))
        result = await test_db.execute(stmt)
        project_with_todos = result.scalar_one()

        assert len(project_with_todos.todos) == 3
        assert all(todo.project_id == project.id for todo in project_with_todos.todos)

    @pytest.mark.asyncio
    async def test_todo_hierarchical_relationship(self, test_db, test_user):
        """Test parent-child todo relationships."""
        # Create parent todo
        parent_todo = Todo(
            user_id=test_user.id, title="Parent Task", status="in_progress", priority=4
        )
        test_db.add(parent_todo)
        await test_db.commit()
        await test_db.refresh(parent_todo)

        # Create subtasks
        subtasks = []
        for i in range(2):
            subtask = Todo(
                user_id=test_user.id,
                parent_todo_id=parent_todo.id,
                title=f"Subtask {i}",
                status="todo",
                priority=3,
                ai_generated=True,
            )
            subtasks.append(subtask)
            test_db.add(subtask)

        await test_db.commit()

        # Test parent-child relationships
        stmt = select(Todo).where(Todo.id == parent_todo.id).options(selectinload(Todo.subtasks))
        result = await test_db.execute(stmt)
        parent_with_subtasks = result.scalar_one()

        assert len(parent_with_subtasks.subtasks) == 2

        for subtask in parent_with_subtasks.subtasks:
            assert subtask.parent_todo_id == parent_todo.id
            # Load parent relationship for verification
            stmt_parent = select(Todo).where(Todo.id == subtask.id).options(selectinload(Todo.parent))
            result_parent = await test_db.execute(stmt_parent)
            subtask_with_parent = result_parent.scalar_one()
            assert subtask_with_parent.parent.id == parent_todo.id

    @pytest.mark.asyncio
    async def test_user_cascade_deletion(self, test_db):
        """Test that deleting user cascades to related objects."""
        # Create user
        user = User(
            clerk_user_id=f"clerk_user_{uuid.uuid4()}",
            email="cascade@example.com",
            username="cascadeuser",
        )
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)

        # Create related objects
        project = Project(
            user_id=user.id,
            name="Cascade Project",
            description="Will be deleted with user",
        )
        test_db.add(project)
        await test_db.flush()

        todo = Todo(user_id=user.id, project_id=project.id, title="Cascade Todo", status="todo")
        test_db.add(todo)
        await test_db.flush()  # Ensure todo.id is available

        ai_interaction = AITodoInteraction(
            user_id=user.id,
            todo_id=todo.id,
            prompt="Test prompt",
            response="Test response",
            interaction_type="subtask_generation",
        )
        test_db.add(ai_interaction)

        await test_db.commit()

        # Store IDs for verification
        project_id = project.id
        todo_id = todo.id
        interaction_id = ai_interaction.id

        # Delete user
        await test_db.delete(user)
        await test_db.commit()

        # Verify cascade deletion
        deleted_project = await test_db.get(Project, project_id)
        deleted_todo = await test_db.get(Todo, todo_id)
        deleted_interaction = await test_db.get(AITodoInteraction, interaction_id)

        assert deleted_project is None
        assert deleted_todo is None
        assert deleted_interaction is None

    @pytest.mark.asyncio
    async def test_todo_completion_timestamp_handling(self, test_db, test_user):
        """Test automatic handling of completion timestamps."""
        todo_service = TodoService(test_db)

        # Create todo
        from app.schemas.todo import TodoCreate, TodoUpdate

        todo_data = TodoCreate(title="Completion Test Todo", status="todo")

        todo = await todo_service.create_todo(todo_data, test_user.id)
        assert todo.completed_at is None

        # Mark as completed
        update_data = TodoUpdate(status="done")
        updated_todo = await todo_service.update_todo(todo.id, update_data, test_user.id)

        assert updated_todo.completed_at is not None
        assert updated_todo.status == "done"

        # Mark as not completed
        update_data = TodoUpdate(status="todo")
        uncompleted_todo = await todo_service.update_todo(todo.id, update_data, test_user.id)

        assert uncompleted_todo.completed_at is None
        assert uncompleted_todo.status == "todo"

    @pytest.mark.asyncio
    async def test_database_constraints_and_indexes(self, test_db):
        """Test database constraints and index performance."""
        # Test that required fields are enforced

        # User without email should fail
        invalid_user = User(
            clerk_user_id=f"clerk_user_{uuid.uuid4()}",
            username="noemailtuser",
            # Missing required email
        )

        test_db.add(invalid_user)
        with pytest.raises(IntegrityError):
            await test_db.commit()

        await test_db.rollback()

        # Todo without title should fail
        invalid_todo = Todo(
            user_id=uuid.uuid4(),  # This will also fail on foreign key
            # Missing required title
            status="todo",
        )

        test_db.add(invalid_todo)
        with pytest.raises(IntegrityError):
            await test_db.commit()

    @pytest.mark.asyncio
    async def test_datetime_timezone_handling(self, test_db, test_user):
        """Test proper handling of timezone-aware datetimes."""
        # Create todo with specific due date
        future_date = datetime.now(timezone.utc) + timedelta(days=7)

        todo = Todo(
            user_id=test_user.id,
            title="Timezone Test Todo",
            status="todo",
            due_date=future_date,
        )

        test_db.add(todo)
        await test_db.commit()
        await test_db.refresh(todo)

        # Verify timezone information is preserved (SQLite may not preserve tzinfo)
        assert todo.due_date is not None
        # In PostgreSQL, timezone info is preserved; in SQLite it may be lost
        if todo.due_date.tzinfo is not None:
            assert todo.due_date.tzinfo == timezone.utc

        # Test completion timestamp
        todo.status = "done"
        todo.completed_at = datetime.now(timezone.utc)
        await test_db.commit()
        await test_db.refresh(todo)

        # Check completion timestamp exists (timezone info may vary by database)
        assert todo.completed_at is not None

    @pytest.mark.asyncio
    async def test_complex_queries_and_aggregations(self, test_db, test_user):
        """Test complex database queries and aggregations."""
        # Create test data
        project = Project(
            user_id=test_user.id,
            name="Query Test Project",
            description="For testing complex queries",
        )
        test_db.add(project)
        await test_db.flush()

        # Create todos with different statuses and priorities
        todo_data = [
            {"title": "High Priority Done", "status": "done", "priority": 5},
            {"title": "Medium Priority Todo", "status": "todo", "priority": 3},
            {
                "title": "High Priority In Progress",
                "status": "in_progress",
                "priority": 5,
            },
            {"title": "Low Priority Done", "status": "done", "priority": 1},
        ]

        for data in todo_data:
            todo = Todo(
                user_id=test_user.id,
                project_id=project.id,
                title=data["title"],
                status=data["status"],
                priority=data["priority"],
            )
            test_db.add(todo)

        await test_db.commit()

        # Test aggregation queries
        # Count todos by status
        status_counts = await test_db.execute(
            select(Todo.status, func.count(Todo.id))
            .where(Todo.user_id == test_user.id)
            .group_by(Todo.status)
        )
        status_dict = dict(status_counts.fetchall())

        assert status_dict["done"] == 2
        assert status_dict["todo"] == 1
        assert status_dict["in_progress"] == 1

        # Average priority
        avg_priority = await test_db.execute(
            select(func.avg(Todo.priority)).where(Todo.user_id == test_user.id)
        )
        avg_value = avg_priority.scalar()
        assert avg_value == 3.5  # (5+3+5+1)/4

        # High priority todos count
        high_priority_count = await test_db.execute(
            select(func.count(Todo.id))
            .where(Todo.user_id == test_user.id)
            .where(Todo.priority >= 4)
        )
        assert high_priority_count.scalar() == 2

    @pytest.mark.asyncio
    async def test_transaction_rollback_behavior(self, test_db, test_user):
        """Test transaction rollback behavior."""
        # Start a transaction and create data
        todo = Todo(
            user_id=test_user.id,
            title="Transaction Test Todo",
            status="todo",
            priority=3,
        )
        test_db.add(todo)
        await test_db.flush()  # Flush but don't commit

        todo_id = todo.id

        # Verify data exists in current transaction
        found_todo = await test_db.get(Todo, todo_id)
        assert found_todo is not None

        # Rollback transaction
        await test_db.rollback()

        # Verify data doesn't exist after rollback
        not_found_todo = await test_db.get(Todo, todo_id)
        assert not_found_todo is None

    @pytest.mark.asyncio
    async def test_ai_interaction_storage(self, test_db, test_user):
        """Test AI interaction storage and retrieval."""
        # Create todo first
        todo = Todo(user_id=test_user.id, title="AI Test Todo", status="todo")
        test_db.add(todo)
        await test_db.commit()
        await test_db.refresh(todo)

        # Create AI interaction
        interaction = AITodoInteraction(
            user_id=test_user.id,
            todo_id=todo.id,
            prompt="Generate subtasks for: AI Test Todo",
            response='{"subtasks": [{"title": "Subtask 1", "priority": 3}]}',
            interaction_type="subtask_generation",
        )

        test_db.add(interaction)
        await test_db.commit()
        await test_db.refresh(interaction)

        # Verify storage and timestamps
        assert interaction.id is not None
        assert interaction.created_at is not None
        assert interaction.updated_at is not None

        # Test retrieval by user
        user_interactions = await test_db.execute(
            select(AITodoInteraction)
            .where(AITodoInteraction.user_id == test_user.id)
            .order_by(AITodoInteraction.created_at.desc())
        )
        interactions_list = user_interactions.scalars().all()

        assert len(interactions_list) >= 1
        assert interactions_list[0].id == interaction.id

    @pytest.mark.asyncio
    async def test_project_todo_statistics_integration(self, test_db, test_user):
        """Test integration between projects and todo statistics."""
        project_service = ProjectService(test_db)
        todo_service = TodoService(test_db)

        # Create project
        from app.schemas.project import ProjectCreate

        project_data = ProjectCreate(
            name="Statistics Project", description="For testing statistics"
        )
        project = await project_service.create_project(project_data, test_user.id)

        # Create todos with different statuses
        from app.schemas.todo import TodoCreate

        todo_configs = [
            {"title": "Todo 1", "status": "todo"},
            {"title": "Todo 2", "status": "done"},
            {"title": "Todo 3", "status": "in_progress"},
            {"title": "Todo 4", "status": "done"},
        ]

        for config in todo_configs:
            todo_data = TodoCreate(
                title=config["title"], status=config["status"], project_id=project.id
            )
            await todo_service.create_todo(todo_data, test_user.id)

        # Test project with todo counts
        project_with_counts = await project_service.get_project_with_todo_counts(
            project.id, test_user.id
        )

        assert project_with_counts is not None
        assert project_with_counts["todo_count"] == 4
        assert project_with_counts["completed_todo_count"] == 2

        # Test user todo statistics
        user_stats = await todo_service.get_user_todo_stats(test_user.id)

        assert user_stats["total_todos"] >= 4
        assert user_stats["completed_todos"] >= 2
        assert user_stats["completion_rate"] > 0

    @pytest.mark.asyncio
    async def test_data_integrity_across_operations(self, test_db, test_user):
        """Test data integrity across multiple operations."""
        user_service = UserService(test_db)
        project_service = ProjectService(test_db)
        todo_service = TodoService(test_db)

        # Create a complete data structure
        from app.schemas.project import ProjectCreate
        from app.schemas.todo import TodoCreate

        # Create project
        project_data = ProjectCreate(name="Integrity Test Project")
        project = await project_service.create_project(project_data, test_user.id)

        # Create parent todo
        parent_todo_data = TodoCreate(
            title="Parent Todo", project_id=project.id, status="in_progress"
        )
        parent_todo = await todo_service.create_todo(parent_todo_data, test_user.id)

        # Create subtasks
        subtask_ids = []
        for i in range(3):
            subtask_data = TodoCreate(
                title=f"Subtask {i}",
                parent_todo_id=parent_todo.id,
                project_id=project.id,
                status="todo",
            )
            subtask = await todo_service.create_todo(subtask_data, test_user.id)
            subtask_ids.append(subtask.id)

        # Verify complete structure
        project_with_todos = await project_service.get_project_with_todos(project.id, test_user.id)

        assert project_with_todos is not None
        assert len(project_with_todos.todos) == 4  # 1 parent + 3 subtasks

        parent_with_subtasks = await todo_service.get_todo_with_subtasks(
            parent_todo.id, test_user.id
        )

        assert parent_with_subtasks is not None
        assert len(parent_with_subtasks.subtasks) == 3

        # Test cascade operations
        # Delete parent todo should cascade to subtasks
        success = await todo_service.delete_todo(parent_todo.id, test_user.id)
        assert success is True

        # Verify subtasks are deleted
        for subtask_id in subtask_ids:
            deleted_subtask = await todo_service.get_todo_by_id(subtask_id, test_user.id)
            assert deleted_subtask is None

        # Project should still exist
        remaining_project = await project_service.get_project_by_id(project.id, test_user.id)
        assert remaining_project is not None
