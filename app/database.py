# python
"""
This module sets up the asynchronous database engine, session factory, and
base class for ORM models using SQLAlchemy. It also provides a utility for
fetching a database session.
"""
from typing import Any, AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
# Prefer a single Base across the app to avoid multiple metadata registries
# from app.models.base import Base  # <- if you have a shared Base defined
from sqlalchemy.ext.declarative import declarative_base
from app.core.config import settings

db_url = (settings.database_url or "").strip()
if not db_url:
    raise RuntimeError(
        "DATABASE_URL is not configured. Set it in the environment or .env file (e.g., DATABASE_URL=postgresql+asyncpg://<user>:<pass>@<host>/<db>)."
    )

engine = create_async_engine(
    db_url,
    echo=settings.debug,
)

AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

# If you have a shared Base, import it instead of creating a new one here.
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, Any]:
    async with AsyncSessionLocal() as session:
        yield session