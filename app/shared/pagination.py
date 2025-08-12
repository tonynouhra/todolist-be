"""Pagination utilities."""

from typing import Dict, Any, TypeVar, Generic
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import Select
from sqlalchemy import func

T = TypeVar('T')


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


async def paginate(
    query: Select,
    db: AsyncSession,
    page: int = 1,
    size: int = 20
) -> Dict[str, Any]:
    """
    Paginate a SQLAlchemy query.
    
    Args:
        query: SQLAlchemy select query
        db: Database session
        page: Page number (1-based)
        size: Page size
        
    Returns:
        Dictionary with pagination info and items
    """
    
    # Get total count
    count_query = select(func.count()).select_from(query.alias())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Calculate pagination info
    total_pages = (total + size - 1) // size  # Ceiling division
    has_next = page < total_pages
    has_prev = page > 1
    
    # Apply pagination to query
    offset = (page - 1) * size
    paginated_query = query.offset(offset).limit(size)
    
    # Execute query
    result = await db.execute(paginated_query)
    items = result.scalars().all()
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "has_next": has_next,
        "has_prev": has_prev,
        "total_pages": total_pages
    }