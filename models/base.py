"""
Defines a base model for SQLAlchemy ORM with common attributes.

This module provides a base class for SQLAlchemy models, including standard
attributes for identifying and timestamping database records. It uses PostgreSQL's
UUID type for primary key generation and automatically manages timestamps for
creation and updates.
"""

from sqlalchemy import Column, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
import uuid
from datetime import datetime

Base = declarative_base()


class BaseModel(Base):
    """
    Base model class for database entities.

    This abstract base model class serves as the foundation for all database
    entities, providing standard fields for consistent identification and
    tracking of record creation and modification timestamps.

    :ivar id: Unique identifier for the record.
    :type id: UUID
    :ivar created_at: Timestamp representing when the record was created.
    :type created_at: datetime
    :ivar updated_at: Timestamp representing when the record was last updated.
    :type updated_at: datetime
    """
    __abstract__ = True

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
