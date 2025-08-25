"""
Partitioned Todo service layer with business logic for scalable database structure.

This service works with the new partitioned database structure:
- TodoActive for active todos (todo, in_progress)
- TodoArchived for completed todos (done)
- AITodoInteraction for AI interaction history

The service provides backward compatibility while leveraging the new partitioned structure
for optimal performance.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Union
from uuid import UUID
from sqlalchemy import and_, or_, desc, asc, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError

from models.todo_partitioned import TodoActive, TodoArchived, AITodoInteraction, Todo
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


class PartitionedTodoService:
    """Service class for partitioned todo business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_todo(
        self, todo_data: TodoCreate, user_id: UUID, generate_ai_subtasks: bool = False
    ) -> TodoActive:
        """Create a new todo in the active partition."""

        # Validate parent todo exists and belongs to user (within active partition)
        depth = 0
        if todo_data.parent_todo_id:
            parent_todo = await self._get_active_todo_by_id_and_user(
                todo_data.parent_todo_id, user_id
            )
            if not parent_todo:
                raise TodoNotFoundError("Parent todo not found")
            depth = parent_todo.depth + 1
            if depth > 10:
                raise MaxTodoDepthExceededError("Maximum todo nesting depth exceeded")

        due_date = (
            self._normalize_datetime(todo_data.due_date) if todo_data.due_date else None
        )

        # Create todo instance in active partition
        todo = TodoActive(
            user_id=user_id,
            project_id=todo_data.project_id,
            parent_todo_id=todo_data.parent_todo_id,
            title=todo_data.title,
            description=todo_data.description,
            status=todo_data.status,
            priority=todo_data.priority,
            due_date=due_date,
            ai_generated=todo_data.ai_generated,
            depth=depth,
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

    async def get_todo_by_id(
        self, todo_id: UUID, user_id: UUID, include_archived: bool = False
    ) -> Optional[Union[TodoActive, TodoArchived]]:
        """Get a todo by ID for a specific user from active or archived partitions."""

        # First check active partition
        active_todo = await self._get_active_todo_by_id_and_user(todo_id, user_id)
        if active_todo:
            return active_todo

        # If not found and include_archived is True, check archived partition
        if include_archived:
            return await self._get_archived_todo_by_id_and_user(todo_id, user_id)

        return None

    async def get_todos_list(
        self,
        user_id: UUID,
        filters: TodoFilter,
        pagination: PaginationParams,
        include_archived: bool = False,
    ) -> Dict[str, Any]:
        """Get paginated list of todos with filters from active and optionally archived partitions."""

        if include_archived:
            return await self._get_todos_from_both_partitions(
                user_id, filters, pagination
            )
        else:
            return await self._get_active_todos_only(user_id, filters, pagination)

    async def get_todo_with_subtasks(
        self, todo_id: UUID, user_id: UUID, include_archived: bool = False
    ) -> Optional[Union[TodoActive, TodoArchived]]:
        """Get todo with all its subtasks from appropriate partitions."""

        # Get the parent todo
        parent_todo = await self.get_todo_by_id(todo_id, user_id, include_archived)
        if not parent_todo:
            return None

        # If it's active, get active subtasks
        if isinstance(parent_todo, TodoActive):
            # Load active subtasks
            subtasks_query = (
                select(TodoActive)
                .where(
                    and_(
                        TodoActive.parent_todo_id == todo_id,
                        TodoActive.user_id == user_id,
                    )
                )
                .order_by(TodoActive.priority.desc(), TodoActive.created_at)
            )

            result = await self.db.execute(subtasks_query)
            subtasks = result.scalars().all()

            # Manually set the subtasks relationship
            parent_todo._subtasks = subtasks

        return parent_todo

    async def update_todo(
        self, todo_id: UUID, todo_data: TodoUpdate, user_id: UUID
    ) -> Optional[TodoActive]:
        """Update a todo (only active todos can be updated)."""

        todo = await self._get_active_todo_by_id_and_user(todo_id, user_id)
        if not todo:
            raise TodoNotFoundError(
                "Todo not found or cannot be updated (might be archived)"
            )

        # Update fields
        update_data = todo_data.model_dump(exclude_unset=True, exclude_none=False)

        # Validate project ownership if project_id is being updated
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

            # If status was changed to 'done', the maintenance job will archive it later
            # For now it stays in the active partition

            return todo
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise InvalidTodoOperationError(f"Failed to update todo: {str(e)}")

    async def delete_todo(self, todo_id: UUID, user_id: UUID) -> bool:
        """Delete a todo and all its subtasks (only from active partition)."""

        todo = await self._get_active_todo_by_id_and_user(todo_id, user_id)
        if not todo:
            raise TodoNotFoundError(
                "Todo not found or cannot be deleted (might be archived)"
            )

        try:
            # First delete all subtasks (recursive)
            await self._delete_subtasks_recursive(todo_id, user_id)

            # Delete the todo itself
            await self.db.delete(todo)
            await self.db.commit()
            return True
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise InvalidTodoOperationError(f"Failed to delete todo: {str(e)}")

    async def toggle_todo_status(
        self, todo_id: UUID, user_id: UUID
    ) -> Optional[TodoActive]:
        """Toggle todo status between todo and done (only for active todos)."""

        todo = await self._get_active_todo_by_id_and_user(todo_id, user_id)
        if not todo:
            raise TodoNotFoundError(
                "Todo not found or cannot be modified (might be archived)"
            )

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
        """Get comprehensive todo statistics for a user from both partitions."""

        # Active todos statistics
        active_total_query = select(func.count(TodoActive.id)).where(
            TodoActive.user_id == user_id
        )
        active_total = await self.db.scalar(active_total_query) or 0

        active_completed_query = select(func.count(TodoActive.id)).where(
            and_(TodoActive.user_id == user_id, TodoActive.status == "done")
        )
        active_completed = await self.db.scalar(active_completed_query) or 0

        active_in_progress_query = select(func.count(TodoActive.id)).where(
            and_(TodoActive.user_id == user_id, TodoActive.status == "in_progress")
        )
        active_in_progress = await self.db.scalar(active_in_progress_query) or 0

        # Archived todos statistics
        archived_total_query = select(func.count(TodoArchived.id)).where(
            TodoArchived.user_id == user_id
        )
        archived_total = await self.db.scalar(archived_total_query) or 0

        # Overdue todos (only from active partition)
        now = datetime.now(timezone.utc)
        overdue_query = select(func.count(TodoActive.id)).where(
            and_(
                TodoActive.user_id == user_id,
                TodoActive.due_date < now,
                TodoActive.status != "done",
            )
        )
        overdue_todos = await self.db.scalar(overdue_query) or 0

        # Calculate totals
        total_todos = active_total + archived_total
        total_completed = (
            active_completed + archived_total
        )  # All archived are completed
        pending_todos = active_total - active_completed - active_in_progress

        return {
            "total_todos": total_todos,
            "active_todos": active_total,
            "archived_todos": archived_total,
            "completed_todos": total_completed,
            "in_progress_todos": active_in_progress,
            "pending_todos": pending_todos,
            "overdue_todos": overdue_todos,
            "completion_rate": (total_completed / total_todos * 100)
            if total_todos > 0
            else 0,
        }

    async def move_completed_todos_to_archive(self, days_old: int = 30) -> int:
        """
        Manual archival method for moving completed todos to archive partition.

        Returns the number of todos archived.
        Note: This is typically handled by automated maintenance jobs.
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)

        # Find completed todos older than cutoff
        query = select(TodoActive).where(
            and_(TodoActive.status == "done", TodoActive.completed_at < cutoff_date)
        )

        result = await self.db.execute(query)
        todos_to_archive = result.scalars().all()

        archived_count = 0
        for todo in todos_to_archive:
            # Create archived version
            archived_todo = TodoArchived(
                id=todo.id,
                user_id=todo.user_id,
                project_id=todo.project_id,
                parent_todo_id=todo.parent_todo_id,
                title=todo.title,
                description=todo.description,
                status=todo.status,
                priority=todo.priority,
                due_date=todo.due_date,
                completed_at=todo.completed_at,
                ai_generated=todo.ai_generated,
                depth=todo.depth,
                created_at=todo.created_at,
                updated_at=todo.updated_at,
            )

            # Add to archive and remove from active
            self.db.add(archived_todo)
            await self.db.delete(todo)
            archived_count += 1

        try:
            await self.db.commit()
            return archived_count
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise InvalidTodoOperationError(f"Failed to archive todos: {str(e)}")

    # Private helper methods

    async def _get_active_todo_by_id_and_user(
        self, todo_id: UUID, user_id: UUID
    ) -> Optional[TodoActive]:
        """Get active todo by ID and user ID."""
        query = select(TodoActive).where(
            and_(TodoActive.id == todo_id, TodoActive.user_id == user_id)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _get_archived_todo_by_id_and_user(
        self, todo_id: UUID, user_id: UUID
    ) -> Optional[TodoArchived]:
        """Get archived todo by ID and user ID."""
        query = select(TodoArchived).where(
            and_(TodoArchived.id == todo_id, TodoArchived.user_id == user_id)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _get_active_todos_only(
        self, user_id: UUID, filters: TodoFilter, pagination: PaginationParams
    ) -> Dict[str, Any]:
        """Get todos from active partition only."""

        query = select(TodoActive).where(TodoActive.user_id == user_id)

        # Apply filters
        query = self._apply_filters_to_query(query, filters, TodoActive)

        # Order by priority (desc) and created_at (desc)
        query = query.order_by(desc(TodoActive.priority), desc(TodoActive.created_at))

        return await paginate(self.db, query, pagination)

    async def _get_todos_from_both_partitions(
        self, user_id: UUID, filters: TodoFilter, pagination: PaginationParams
    ) -> Dict[str, Any]:
        """Get todos from both active and archived partitions."""

        # This is more complex and requires careful implementation
        # For now, we'll get active todos and note that archived integration needs more work
        active_result = await self._get_active_todos_only(user_id, filters, pagination)

        # TODO: Implement proper union query or separate queries and merge results
        # This would require more sophisticated pagination handling

        return active_result

    def _apply_filters_to_query(self, query, filters: TodoFilter, model_class):
        """Apply filters to a query for the given model class."""

        if filters.status:
            query = query.where(model_class.status == filters.status)

        if filters.priority:
            query = query.where(model_class.priority == filters.priority)

        if filters.project_id:
            query = query.where(model_class.project_id == filters.project_id)

        if filters.parent_todo_id:
            query = query.where(model_class.parent_todo_id == filters.parent_todo_id)
        elif filters.parent_todo_id is None:
            query = query.where(model_class.parent_todo_id.is_(None))

        if filters.ai_generated is not None:
            query = query.where(model_class.ai_generated == filters.ai_generated)

        if filters.due_date_from:
            query = query.where(model_class.due_date >= filters.due_date_from)

        if filters.due_date_to:
            query = query.where(model_class.due_date <= filters.due_date_to)

        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.where(
                or_(
                    model_class.title.ilike(search_term),
                    model_class.description.ilike(search_term),
                )
            )

        return query

    async def _delete_subtasks_recursive(self, parent_id: UUID, user_id: UUID):
        """Recursively delete all subtasks of a todo."""

        # Find all subtasks
        subtasks_query = select(TodoActive).where(
            and_(TodoActive.parent_todo_id == parent_id, TodoActive.user_id == user_id)
        )
        result = await self.db.execute(subtasks_query)
        subtasks = result.scalars().all()

        # Recursively delete subtasks
        for subtask in subtasks:
            await self._delete_subtasks_recursive(subtask.id, user_id)
            await self.db.delete(subtask)

    def _normalize_datetime(self, dt: datetime) -> datetime:
        """Normalize datetime to UTC timezone-aware format."""
        if dt is None:
            return None

        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)

    async def _validate_project_ownership(
        self, project_id: UUID, user_id: UUID
    ) -> None:
        """Validate that a project belongs to the user."""
        if project_id:
            query = select(Project).where(
                and_(Project.id == project_id, Project.user_id == user_id)
            )
            result = await self.db.execute(query)
            project = result.scalar_one_or_none()

            if not project:
                raise TodoPermissionError("Project not found or access denied")

    async def _generate_ai_subtasks(self, todo: TodoActive) -> None:
        """Generate AI subtasks for a todo."""
        try:
            from app.domains.ai.service import AIService
            from app.schemas.ai import SubtaskGenerationRequest

            ai_service = AIService(self.db)

            request = SubtaskGenerationRequest(todo_id=todo.id)

            response = await ai_service.generate_subtasks(
                request=request, user_id=todo.user_id
            )

            # Create subtask records in active partition
            for subtask_data in response.generated_subtasks:
                subtask = TodoActive(
                    user_id=todo.user_id,
                    project_id=todo.project_id,
                    parent_todo_id=todo.id,
                    title=subtask_data.title,
                    description=subtask_data.description,
                    status="todo",
                    priority=subtask_data.priority,
                    ai_generated=True,
                    depth=todo.depth + 1,
                )

                self.db.add(subtask)

            await self.db.commit()

        except Exception as e:
            # Don't fail the main todo creation if AI generation fails
            await self.db.rollback()
            pass


# Backward compatibility service wrapper
class TodoService(PartitionedTodoService):
    """
    Backward compatibility wrapper that maintains the original TodoService interface
    while using the new partitioned structure underneath.

    This allows existing code to continue working while gradually migrating to
    the partitioned structure.
    """

    async def create_todo(
        self, todo_data: TodoCreate, user_id: UUID, generate_ai_subtasks: bool = False
    ) -> Todo:
        """Create a new todo and return as compatibility Todo object."""
        active_todo = await super().create_todo(
            todo_data, user_id, generate_ai_subtasks
        )
        return Todo.from_active(active_todo)

    async def get_todo_by_id(self, todo_id: UUID, user_id: UUID) -> Optional[Todo]:
        """Get a todo by ID and return as compatibility Todo object."""
        result = await super().get_todo_by_id(todo_id, user_id, include_archived=True)

        if isinstance(result, TodoActive):
            return Todo.from_active(result)
        elif isinstance(result, TodoArchived):
            return Todo.from_archived(result)

        return None

    # Add similar wrappers for other methods as needed...


# Export both services for different use cases
__all__ = ["PartitionedTodoService", "TodoService"]
