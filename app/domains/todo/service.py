"""Todo service layer with business logic."""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy import and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError

from models.todo import Todo
from models.user import User
from models.project import Project
from app.schemas.todo import TodoCreate, TodoUpdate, TodoFilter
from app.exceptions.todo import (
    TodoNotFoundError,
    TodoPermissionError,
    InvalidTodoOperationError,
    MaxTodoDepthExceededError,
)
from app.shared.pagination import PaginationParams, paginate


class TodoService:
    """Service class for todo business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_todo(
        self, todo_data: TodoCreate, user_id: UUID, generate_ai_subtasks: bool = False
    ) -> Todo:
        """Create a new todo."""

        # Validate parent todo exists and belongs to user
        if todo_data.parent_todo_id:
            parent_todo = await self._get_todo_by_id_and_user(
                todo_data.parent_todo_id, user_id
            )
            if not parent_todo:
                raise TodoNotFoundError("Parent todo not found")
            depth = await self._get_todo_depth(parent_todo)
            if depth >= 5:
                raise MaxTodoDepthExceededError("Maximum todo nesting depth exceeded")

        due_date = (
            self._normalize_datetime(todo_data.due_date) if todo_data.due_date else None
        )

        # Create todo instance
        todo = Todo(
            user_id=user_id,
            project_id=todo_data.project_id,
            parent_todo_id=todo_data.parent_todo_id,
            title=todo_data.title,
            description=todo_data.description,
            status=todo_data.status,
            priority=todo_data.priority,
            due_date=due_date,
            ai_generated=todo_data.ai_generated,
        )

        try:
            self.db.add(todo)
            await self.db.commit()
            await self.db.refresh(todo)

            # Generate AI subtasks if requested
            if generate_ai_subtasks and not todo_data.parent_todo_id:
                await self._generate_ai_subtasks(todo)

            return todo
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise InvalidTodoOperationError(f"Failed to create todo: {str(e)}")

    async def get_todo_by_id(self, todo_id: UUID, user_id: UUID) -> Optional[Todo]:
        """Get a todo by ID for a specific user."""
        return await self._get_todo_by_id_and_user(todo_id, user_id)

    async def get_todos_list(
        self, user_id: UUID, filters: TodoFilter, pagination: PaginationParams
    ) -> Dict[str, Any]:
        """Get paginated list of todos with filters."""

        query = select(Todo).where(Todo.user_id == user_id)

        # Apply filters
        if filters.status:
            query = query.where(Todo.status == filters.status)

        if filters.priority:
            query = query.where(Todo.priority == filters.priority)

        if filters.project_id:
            query = query.where(Todo.project_id == filters.project_id)

        if filters.parent_todo_id:
            query = query.where(Todo.parent_todo_id == filters.parent_todo_id)
        elif filters.parent_todo_id is None:
            # Only top-level todos if explicitly requested
            query = query.where(Todo.parent_todo_id.is_(None))

        if filters.ai_generated is not None:
            query = query.where(Todo.ai_generated == filters.ai_generated)

        if filters.due_date_from:
            query = query.where(Todo.due_date >= filters.due_date_from)

        if filters.due_date_to:
            query = query.where(Todo.due_date <= filters.due_date_to)

        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.where(
                or_(Todo.title.ilike(search_term), Todo.description.ilike(search_term))
            )

        # Order by priority (desc) and created_at (desc)
        query = query.order_by(desc(Todo.priority), desc(Todo.created_at))

        return await paginate(self.db, query, pagination)

    async def get_todo_with_subtasks(
        self, todo_id: UUID, user_id: UUID
    ) -> Optional[Todo]:
        """Get todo with all its subtasks."""
        query = (
            select(Todo)
            .options(selectinload(Todo.subtasks))
            .where(and_(Todo.id == todo_id, Todo.user_id == user_id))
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_todo(
        self, todo_id: UUID, todo_data: TodoUpdate, user_id: UUID
    ) -> Optional[Todo]:
        """Update a todo."""

        todo = await self._get_todo_by_id_and_user(todo_id, user_id)
        if not todo:
            raise TodoNotFoundError("Todo not found")

        # Update fields - include None values to allow unsetting fields
        update_data = todo_data.model_dump(exclude_unset=True, exclude_none=False)

        # Validate project ownership if project_id is being updated (and not being unset)
        if "project_id" in update_data and update_data["project_id"] is not None:
            await self._validate_project_ownership(update_data["project_id"], user_id)

        for field, value in update_data.items():
            if hasattr(todo, field):
                # Normalize datetime fields
                if field == "due_date" and value is not None:
                    value = self._normalize_datetime(value)
                elif field == "completed_at" and value is not None:
                    value = self._normalize_datetime(value)
                setattr(todo, field, value)

        # Auto-set completed_at when status changes to 'done'
        if todo_data.status == "done" and todo.status != "done":
            todo.completed_at = datetime.now(timezone.utc)
        elif todo_data.status and todo_data.status != "done":
            todo.completed_at = None

        try:
            await self.db.commit()
            await self.db.refresh(todo)
            return todo
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise InvalidTodoOperationError(f"Failed to update todo: {str(e)}")

    async def delete_todo(self, todo_id: UUID, user_id: UUID) -> bool:
        """Delete a todo and all its subtasks."""

        todo = await self._get_todo_by_id_and_user(todo_id, user_id)
        if not todo:
            raise TodoNotFoundError("Todo not found")

        try:
            # Delete todo (cascade will handle subtasks)
            await self.db.delete(todo)
            await self.db.commit()
            return True
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise InvalidTodoOperationError(f"Failed to delete todo: {str(e)}")

    async def toggle_todo_status(self, todo_id: UUID, user_id: UUID) -> Optional[Todo]:
        """Toggle todo status between todo and done."""

        todo = await self._get_todo_by_id_and_user(todo_id, user_id)
        if not todo:
            raise TodoNotFoundError("Todo not found")

        if todo.status == "done":
            todo.status = "todo"
            todo.completed_at = None
        else:
            todo.status = "done"
            todo.completed_at = datetime.now(timezone.utc)

        try:
            await self.db.commit()
            await self.db.refresh(todo)
            return todo
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise InvalidTodoOperationError(f"Failed to toggle todo status: {str(e)}")

    async def get_user_todo_stats(self, user_id: UUID) -> Dict[str, Any]:
        """Get todo statistics for a user."""

        # Total todos
        total_query = select(Todo).where(Todo.user_id == user_id)
        total_result = await self.db.execute(total_query)
        total_todos = len(total_result.scalars().all())

        # Completed todos
        completed_query = select(Todo).where(
            and_(Todo.user_id == user_id, Todo.status == "done")
        )
        completed_result = await self.db.execute(completed_query)
        completed_todos = len(completed_result.scalars().all())

        # In progress todos
        in_progress_query = select(Todo).where(
            and_(Todo.user_id == user_id, Todo.status == "in_progress")
        )
        in_progress_result = await self.db.execute(in_progress_query)
        in_progress_todos = len(in_progress_result.scalars().all())

        # Overdue todos
        now = datetime.now(timezone.utc)
        overdue_query = select(Todo).where(
            and_(Todo.user_id == user_id, Todo.due_date < now, Todo.status != "done")
        )
        overdue_result = await self.db.execute(overdue_query)
        overdue_todos = len(overdue_result.scalars().all())

        return {
            "total_todos": total_todos,
            "completed_todos": completed_todos,
            "in_progress_todos": in_progress_todos,
            "pending_todos": total_todos - completed_todos - in_progress_todos,
            "overdue_todos": overdue_todos,
            "completion_rate": (completed_todos / total_todos * 100)
            if total_todos > 0
            else 0,
        }

    # Private helper methods

    async def _get_todo_by_id_and_user(
        self, todo_id: UUID, user_id: UUID
    ) -> Optional[Todo]:
        """Get todo by ID and user ID."""
        query = select(Todo).where(and_(Todo.id == todo_id, Todo.user_id == user_id))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _get_todo_depth(self, todo: Todo) -> int:
        """Calculate the depth of a todo in the hierarchy."""
        depth = 0
        current_todo = todo

        while current_todo.parent_todo_id:
            depth += 1
            parent_query = select(Todo).where(Todo.id == current_todo.parent_todo_id)
            result = await self.db.execute(parent_query)
            current_todo = result.scalar_one_or_none()

            if not current_todo:
                break

        return depth

    def _normalize_datetime(self, dt: datetime) -> datetime:
        """Normalize datetime to UTC timezone-aware format."""
        if dt is None:
            return None

        # If datetime is timezone-naive, assume it's UTC
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)

        # If datetime is timezone-aware, convert to UTC
        return dt.astimezone(timezone.utc)

    async def _validate_project_ownership(
        self, project_id: UUID, user_id: UUID
    ) -> None:
        """Validate that a project belongs to the user."""
        if project_id:  # Allow None/null values for removing project assignment
            query = select(Project).where(
                and_(Project.id == project_id, Project.user_id == user_id)
            )
            result = await self.db.execute(query)
            project = result.scalar_one_or_none()

            if not project:
                raise TodoPermissionError("Project not found or access denied")

    async def _generate_ai_subtasks(self, todo: Todo) -> None:
        """Generate AI subtasks for a todo."""
        try:
            from app.domains.ai.service import AIService
            from app.schemas.ai import SubtaskGenerationRequest

            # Create AI service instance
            ai_service = AIService(self.db)

            # Build the request
            request = SubtaskGenerationRequest(
                title=todo.title,
                description=todo.description,
                priority=todo.priority,
                due_date=todo.due_date,
                max_subtasks=5,
            )

            # Generate subtasks using AI
            response = await ai_service.generate_subtasks(
                request=request, user_id=todo.user_id, todo_id=todo.id
            )

            # Create subtask records in database
            for subtask_data in response.generated_subtasks:
                subtask = Todo(
                    user_id=todo.user_id,
                    project_id=todo.project_id,  # Inherit parent's project
                    parent_todo_id=todo.id,
                    title=subtask_data.title,
                    description=subtask_data.description,
                    status="todo",
                    priority=subtask_data.priority,
                    ai_generated=True,
                )

                self.db.add(subtask)

            # Commit all subtasks
            await self.db.commit()

            logger.info(
                f"Generated {len(response.generated_subtasks)} AI subtasks for todo {todo.id}"
            )

        except Exception as e:
            logger.warning(
                f"Failed to generate AI subtasks for todo {todo.id}: {str(e)}"
            )
            # Don't fail the main todo creation if AI generation fails
            await self.db.rollback()
            pass
