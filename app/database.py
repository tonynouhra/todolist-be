# python
"""Database engine and session utilities.

This module sets up the asynchronous database engine, session factory, and base
class for ORM models using SQLAlchemy. It also provides a utility for fetching
an asynchronous database session.
"""
import os
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Prefer a single Base across the app to avoid multiple metadata registries
# from app.models.base import Base  # <- if you have a shared Base defined
from sqlalchemy.ext.declarative import declarative_base

from app.core.config import settings

# For testing, prioritize TEST_DATABASE_URL
DB_URL = None
if os.getenv("TESTING") == "true":
    DB_URL = os.getenv("TEST_DATABASE_URL") or settings.test_database_url
else:
    DB_URL = settings.database_url

DB_URL = (DB_URL or "").strip()
if not DB_URL:
    raise RuntimeError(
        "DATABASE_URL is not configured. Set it in the environment or .env file (e.g., DATABASE_URL=postgresql+asyncpg://<user>:<pass>@<host>/<db>)."
    )

engine = create_async_engine(
    DB_URL,
    echo=settings.debug,
)

AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

# If you have a shared Base, import it instead of creating a new one here.
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, Any]:
    async with AsyncSessionLocal() as session:
        yield session
