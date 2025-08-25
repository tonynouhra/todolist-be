"""Pagination utilities."""

from typing import Any, Dict, Generic, TypeVar

from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import Select

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Pagination parameters."""

    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    size: int = Field(default=20, ge=1, le=100, description="Page size")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""

    items: list[T]
    total: int
    page: int
    size: int
    has_next: bool
    has_prev: bool
    total_pages: int


async def paginate(db: AsyncSession, query: Select, pagination: PaginationParams) -> Dict[str, Any]:
    """
    Paginate a SQLAlchemy query.

    Args:
        db: Database session
        query: SQLAlchemy select query
        pagination: Pagination parameters

    Returns:
        Dictionary with pagination info and items
    """

    # Get total count by creating a count query from the original query's subquery
    subquery = query.subquery()
    count_query = select(func.count()).select_from(subquery)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Calculate pagination info
    total_pages = (total + pagination.size - 1) // pagination.size  # Ceiling division
    has_next = pagination.page < total_pages
    has_prev = pagination.page > 1

    # Apply pagination to query
    offset = (pagination.page - 1) * pagination.size
    paginated_query = query.offset(offset).limit(pagination.size)

    # Execute query
    result = await db.execute(paginated_query)
    items = result.scalars().all()

    return {
        "items": items,
        "total": total,
        "page": pagination.page,
        "size": pagination.size,
        "has_next": has_next,
        "has_prev": has_prev,
        "total_pages": total_pages,
    }
