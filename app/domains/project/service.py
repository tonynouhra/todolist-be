"""Project service layer with business logic."""

from typing import Optional, List, Dict, Any
from uuid import UUID
from sqlalchemy import and_, or_, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError

from models.project import Project
from models.todo import Todo
from models.user import User
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectFilter
from app.exceptions.base import NotFoundError, PermissionError, ValidationError
from app.shared.pagination import PaginationParams, paginate


class ProjectService:
    """Service class for project business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_project(self, project_data: ProjectCreate, user_id: UUID) -> Project:
        """Create a new project."""

        # Check if project name already exists for this user
        existing = await self._get_project_by_name_and_user(project_data.name, user_id)
        if existing:
            raise ValidationError("A project with this name already exists")

        project = Project(
            user_id=user_id,
            name=project_data.name,
            description=project_data.description,
        )

        try:
            self.db.add(project)
            await self.db.commit()
            await self.db.refresh(project)
            return project
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise ValidationError(f"Failed to create project: {str(e)}")

    async def get_project_by_id(self, project_id: UUID, user_id: UUID) -> Optional[Project]:
        """Get a project by ID, ensuring it belongs to the user."""
        return await self._get_project_by_id_and_user(project_id, user_id)

    async def get_project_with_todos(self, project_id: UUID, user_id: UUID) -> Optional[Project]:
        """Get a project with its todos."""

        stmt = (
            select(Project)
            .options(selectinload(Project.todos))
            .where(and_(Project.id == project_id, Project.user_id == user_id))
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_projects_list(
        self,
        user_id: UUID,
        filters: Optional[ProjectFilter] = None,
        pagination: Optional[PaginationParams] = None,
    ) -> Dict[str, Any]:
        """Get paginated list of projects with optional filters."""

        # Build base query
        stmt = select(Project).where(Project.user_id == user_id)

        # Add filters
        if filters:
            if filters.search:
                search_term = f"%{filters.search}%"
                stmt = stmt.where(
                    or_(
                        Project.name.ilike(search_term),
                        Project.description.ilike(search_term),
                    )
                )

        # Add ordering
        stmt = stmt.order_by(desc(Project.updated_at))

        # Apply pagination
        if pagination:
            return await paginate(self.db, stmt, pagination)
        else:
            result = await self.db.execute(stmt)
            projects = result.scalars().all()
            return {
                "items": projects,
                "total": len(projects),
                "page": 1,
                "size": len(projects),
                "has_next": False,
                "has_prev": False,
            }

    async def update_project(
        self, project_id: UUID, project_data: ProjectUpdate, user_id: UUID
    ) -> Project:
        """Update a project."""

        project = await self._get_project_by_id_and_user(project_id, user_id)
        if not project:
            raise NotFoundError("Project not found")

        # Check if new name conflicts with existing project
        if project_data.name and project_data.name != project.name:
            existing = await self._get_project_by_name_and_user(project_data.name, user_id)
            if existing:
                raise ValidationError("A project with this name already exists")

        # Update fields
        update_data = project_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(project, field, value)

        try:
            await self.db.commit()
            await self.db.refresh(project)
            return project
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise ValidationError(f"Failed to update project: {str(e)}")

    async def delete_project(self, project_id: UUID, user_id: UUID) -> bool:
        """Delete a project and handle todos."""

        project = await self._get_project_by_id_and_user(project_id, user_id)
        if not project:
            raise NotFoundError("Project not found")

        try:
            # Check if project has todos
            todo_count = await self._get_project_todo_count(project_id)
            if todo_count > 0:
                # Option 1: Set todos' project_id to None instead of deleting
                await self._unassign_todos_from_project(project_id)
                # Option 2: Delete all todos (uncomment if preferred)
                # await self._delete_project_todos(project_id)

            await self.db.delete(project)
            await self.db.commit()
            return True
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise ValidationError(f"Failed to delete project: {str(e)}")

    async def get_project_stats(self, user_id: UUID) -> Dict[str, Any]:
        """Get project statistics for a user."""

        # Total projects
        total_stmt = select(func.count(Project.id)).where(Project.user_id == user_id)
        total_result = await self.db.execute(total_stmt)
        total_projects = total_result.scalar() or 0

        # Projects with todos
        projects_with_todos_stmt = (
            select(func.count(func.distinct(Project.id)))
            .select_from(Project)
            .join(Todo, Project.id == Todo.project_id, isouter=False)
            .where(Project.user_id == user_id)
        )
        projects_with_todos_result = await self.db.execute(projects_with_todos_stmt)
        projects_with_todos = projects_with_todos_result.scalar() or 0

        # Average todos per project - using subquery to avoid nested aggregates
        todo_counts_subquery = (
            select(Project.id.label("project_id"), func.count(Todo.id).label("todo_count"))
            .select_from(Project)
            .join(Todo, Project.id == Todo.project_id, isouter=True)
            .where(Project.user_id == user_id)
            .group_by(Project.id)
        ).subquery()

        avg_todos_stmt = select(func.avg(todo_counts_subquery.c.todo_count))
        avg_todos_result = await self.db.execute(avg_todos_stmt)
        avg_todos = avg_todos_result.scalar() or 0.0

        return {
            "total_projects": total_projects,
            "projects_with_todos": projects_with_todos,
            "average_todos_per_project": float(avg_todos),
        }

    async def get_project_with_todo_counts(
        self, project_id: UUID, user_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Get project with todo counts."""

        project = await self._get_project_by_id_and_user(project_id, user_id)
        if not project:
            return None

        # Get todo counts
        total_todos_stmt = select(func.count(Todo.id)).where(
            and_(Todo.project_id == project_id, Todo.user_id == user_id)
        )
        total_result = await self.db.execute(total_todos_stmt)
        total_todos = total_result.scalar() or 0

        completed_todos_stmt = select(func.count(Todo.id)).where(
            and_(
                Todo.project_id == project_id,
                Todo.user_id == user_id,
                Todo.status == "done",
            )
        )
        completed_result = await self.db.execute(completed_todos_stmt)
        completed_todos = completed_result.scalar() or 0

        project_dict = {
            "id": project.id,
            "user_id": project.user_id,
            "name": project.name,
            "description": project.description,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
            "todo_count": total_todos,
            "completed_todo_count": completed_todos,
        }

        return project_dict

    # Private helper methods
    async def _get_project_by_id_and_user(
        self, project_id: UUID, user_id: UUID
    ) -> Optional[Project]:
        """Get project by ID and user ID."""
        stmt = select(Project).where(and_(Project.id == project_id, Project.user_id == user_id))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_project_by_name_and_user(self, name: str, user_id: UUID) -> Optional[Project]:
        """Get project by name and user ID."""
        stmt = select(Project).where(and_(Project.name == name, Project.user_id == user_id))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_project_todo_count(self, project_id: UUID) -> int:
        """Get count of todos in a project."""
        stmt = select(func.count(Todo.id)).where(Todo.project_id == project_id)
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def _unassign_todos_from_project(self, project_id: UUID):
        """Set project_id to None for all todos in the project."""
        stmt = select(Todo).where(Todo.project_id == project_id)
        result = await self.db.execute(stmt)
        todos = result.scalars().all()

        for todo in todos:
            todo.project_id = None

    async def _delete_project_todos(self, project_id: UUID):
        """Delete all todos in a project."""
        stmt = select(Todo).where(Todo.project_id == project_id)
        result = await self.db.execute(stmt)
        todos = result.scalars().all()

        for todo in todos:
            await self.db.delete(todo)
