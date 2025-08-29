"""Todo API controller with FastAPI endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, validate_token
from app.domains.todo.service import TodoService
from app.schemas.base import ResponseSchema
from app.schemas.todo import (
    TodoCreate,
    TodoFilter,
    TodoListResponse,
    TodoResponse,
    TodoUpdate,
    TodoWithSubtasks,
)
from app.shared.pagination import PaginationParams
from models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/todos",
    tags=["todos"],
    dependencies=[Depends(validate_token)],  # Global token validation for all routes
)


@router.post("/", response_model=ResponseSchema, status_code=201)
async def create_todo(
    _request: Request,
    todo_data: TodoCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new todo."""
    service = TodoService(db)
    todo = await service.create_todo(
        todo_data=todo_data,
        user_id=current_user.id,
        generate_ai_subtasks=todo_data.generate_ai_subtasks,
    )

    return ResponseSchema(
        status="success",
        message="Todo created successfully",
        data=TodoResponse.model_validate(todo).model_dump(),
    )


@router.get("/", response_model=TodoListResponse)
async def get_todos(
    _request: Request,
    status: str | None = Query(None, regex="^(todo|in_progress|done)$"),
    priority: int | None = Query(None, ge=1, le=5),
    project_id: UUID | None = Query(None),
    parent_todo_id: UUID | None = Query(None),
    ai_generated: bool | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get paginated list of todos with optional filters."""
    filters = TodoFilter(
        status=status,
        priority=priority,
        project_id=project_id,
        parent_todo_id=parent_todo_id,
        ai_generated=ai_generated,
        search=search,
    )

    pagination = PaginationParams(page=page, size=size)

    service = TodoService(db)
    result = await service.get_todos_list(
        user_id=current_user.id, filters=filters, pagination=pagination
    )

    todos = [TodoResponse.model_validate(todo) for todo in result["items"]]

    return TodoListResponse(
        todos=todos,
        total=result["total"],
        page=result["page"],
        size=result["size"],
        has_next=result["has_next"],
        has_prev=result["has_prev"],
    )


@router.get("/{todo_id}", response_model=ResponseSchema)
async def get_todo(
    _request: Request,
    todo_id: UUID = Path(..., description="Todo ID"),
    include_subtasks: bool = Query(False, description="Include subtasks in response"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific todo by ID."""
    service = TodoService(db)

    if include_subtasks:
        todo = await service.get_todo_with_subtasks(todo_id, current_user.id)
        todo_data = TodoWithSubtasks.model_validate(todo) if todo else None
    else:
        todo = await service.get_todo_by_id(todo_id, current_user.id)
        todo_data = TodoResponse.model_validate(todo) if todo else None

    if not todo_data:
        return ResponseSchema(status="error", message="Todo not found", data=None)

    return ResponseSchema(
        status="success",
        message="Todo retrieved successfully",
        data=todo_data.model_dump(),
    )


@router.put("/{todo_id}", response_model=ResponseSchema)
async def update_todo(
    _request: Request,
    todo_id: UUID = Path(..., description="Todo ID"),
    todo_data: TodoUpdate = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a specific todo."""
    service = TodoService(db)
    todo = await service.update_todo(todo_id, todo_data, current_user.id)

    return ResponseSchema(
        status="success",
        message="Todo updated successfully",
        data=TodoResponse.model_validate(todo).model_dump(),
    )


@router.delete("/{todo_id}", response_model=ResponseSchema)
async def delete_todo(
    _request: Request,
    todo_id: UUID = Path(..., description="Todo ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a specific todo and all its subtasks."""
    service = TodoService(db)
    success = await service.delete_todo(todo_id, current_user.id)

    return ResponseSchema(
        status="success" if success else "error",
        message="Todo deleted successfully" if success else "Failed to delete todo",
        data=None,
    )


@router.patch("/{todo_id}/toggle-status", response_model=ResponseSchema)
async def toggle_todo_status(
    _request: Request,
    todo_id: UUID = Path(..., description="Todo ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Toggle todo status between todo and done."""
    service = TodoService(db)
    todo = await service.toggle_todo_status(todo_id, current_user.id)

    return ResponseSchema(
        status="success",
        message="Todo status toggled successfully",
        data=TodoResponse.model_validate(todo).model_dump(),
    )


@router.get("/stats/summary", response_model=ResponseSchema)
async def get_todo_stats(
    _request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get todo statistics for the current user."""
    service = TodoService(db)
    stats = await service.get_user_todo_stats(current_user.id)

    return ResponseSchema(
        status="success", message="Todo statistics retrieved successfully", data=stats
    )


@router.get("/{todo_id}/subtasks", response_model=TodoListResponse)
async def get_todo_subtasks(
    _request: Request,
    todo_id: UUID = Path(..., description="Todo ID"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get subtasks of a specific todo."""
    # First verify the parent todo exists and belongs to user
    service = TodoService(db)
    parent_todo = await service.get_todo_by_id(todo_id, current_user.id)
    if not parent_todo:
        from app.exceptions.base import NotFoundError

        raise NotFoundError("Todo not found")

    filters = TodoFilter(parent_todo_id=todo_id)
    pagination = PaginationParams(page=page, size=size)

    result = await service.get_todos_list(
        user_id=current_user.id, filters=filters, pagination=pagination
    )

    todos = [TodoResponse.model_validate(todo) for todo in result["items"]]

    return TodoListResponse(
        todos=todos,
        total=result["total"],
        page=result["page"],
        size=result["size"],
        has_next=result["has_next"],
        has_prev=result["has_prev"],
    )
