"""Project API controller with FastAPI endpoints."""

import logging
from typing import List, Optional
from uuid import UUID
from fastapi import (
    APIRouter,
    Depends,
    Query,
    Path,
    Body,
    Request,
    HTTPException,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_current_user, validate_token
from app.domains.project.service import ProjectService
from app.schemas.project import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectWithTodos,
    ProjectFilter,
    ProjectListResponse,
    ProjectStats,
)

# Import schemas to ensure model rebuilding happens
import app.schemas
from app.schemas.base import ResponseSchema
from app.shared.pagination import PaginationParams
from models.user import User


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/projects",
    tags=["projects"],
    dependencies=[Depends(validate_token)],  # Global token validation for all routes
)


@router.post("/", response_model=ResponseSchema, status_code=201)
async def create_project(
    request: Request,
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new project."""

    service = ProjectService(db)
    project = await service.create_project(
        project_data=project_data, user_id=current_user.id
    )

    return ResponseSchema(
        status="success",
        message="Project created successfully",
        data=ProjectResponse.model_validate(project).model_dump(),
    )


@router.get("/", response_model=ProjectListResponse)
async def get_projects(
    request: Request,
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated list of projects with optional filters."""

    filters = ProjectFilter(search=search)
    pagination = PaginationParams(page=page, size=size)

    service = ProjectService(db)
    result = await service.get_projects_list(
        user_id=current_user.id, filters=filters, pagination=pagination
    )

    projects = []
    for project in result["items"]:
        # Get project with todo counts
        project_with_counts = await service.get_project_with_todo_counts(
            project.id, current_user.id
        )
        if project_with_counts:
            projects.append(ProjectResponse.model_validate(project_with_counts))
        else:
            projects.append(ProjectResponse.model_validate(project))

    return ProjectListResponse(
        projects=projects,
        total=result["total"],
        page=result["page"],
        size=result["size"],
        has_next=result["has_next"],
        has_prev=result["has_prev"],
    )


@router.get("/{project_id}", response_model=ResponseSchema)
async def get_project(
    request: Request,
    project_id: UUID = Path(..., description="Project ID"),
    include_todos: bool = Query(False, description="Include todos in response"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific project by ID."""

    service = ProjectService(db)

    if include_todos:
        project = await service.get_project_with_todos(project_id, current_user.id)
        if project:
            project_data = ProjectWithTodos.model_validate(project)
        else:
            project_data = None
    else:
        # Get project with todo counts
        project_dict = await service.get_project_with_todo_counts(
            project_id, current_user.id
        )
        if project_dict:
            project_data = ProjectResponse.model_validate(project_dict)
        else:
            project_data = None

    if not project_data:
        return ResponseSchema(status="error", message="Project not found", data=None)

    return ResponseSchema(
        status="success",
        message="Project retrieved successfully",
        data=project_data.model_dump(),
    )


@router.put("/{project_id}", response_model=ResponseSchema)
async def update_project(
    request: Request,
    project_id: UUID = Path(..., description="Project ID"),
    project_data: ProjectUpdate = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a specific project."""

    service = ProjectService(db)
    project = await service.update_project(project_id, project_data, current_user.id)

    # Get updated project with todo counts
    project_dict = await service.get_project_with_todo_counts(
        project_id, current_user.id
    )
    if project_dict:
        project_response = ProjectResponse.model_validate(project_dict)
    else:
        project_response = ProjectResponse.model_validate(project)

    return ResponseSchema(
        status="success",
        message="Project updated successfully",
        data=project_response.model_dump(),
    )


@router.delete("/{project_id}", response_model=ResponseSchema)
async def delete_project(
    request: Request,
    project_id: UUID = Path(..., description="Project ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a specific project."""

    service = ProjectService(db)
    success = await service.delete_project(project_id, current_user.id)

    return ResponseSchema(
        status="success" if success else "error",
        message="Project deleted successfully"
        if success
        else "Failed to delete project",
        data=None,
    )


@router.get("/stats/summary", response_model=ResponseSchema)
async def get_project_stats(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get project statistics for the current user."""

    service = ProjectService(db)
    stats = await service.get_project_stats(current_user.id)

    return ResponseSchema(
        status="success",
        message="Project statistics retrieved successfully",
        data=ProjectStats.model_validate(stats).model_dump(),
    )


@router.get("/{project_id}/todos", response_model=ResponseSchema)
async def get_project_todos(
    request: Request,
    project_id: UUID = Path(..., description="Project ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all todos for a specific project."""

    service = ProjectService(db)

    # First verify the project exists and belongs to user
    project = await service.get_project_by_id(project_id, current_user.id)
    if not project:
        return ResponseSchema(status="error", message="Project not found", data=None)

    # Get project with todos
    project_with_todos = await service.get_project_with_todos(
        project_id, current_user.id
    )

    if not project_with_todos:
        return ResponseSchema(status="error", message="Project not found", data=None)

    project_data = ProjectWithTodos.model_validate(project_with_todos)

    return ResponseSchema(
        status="success",
        message="Project todos retrieved successfully",
        data={
            "project": project_data.model_dump(exclude={"todos"}),
            "todos": [todo.model_dump() for todo in project_data.todos],
        },
    )
