"""
Defines a base model for SQLAlchemy ORM with common attributes.

This module provides a base class for SQLAlchemy models, including standard
attributes for identifying and timestamping database records. It uses PostgreSQL's
UUID type for primary key generation and automatically manages timestamps for
creation and updates.
"""

from sqlalchemy import Column, DateTime, String, TypeDecorator
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.ext.declarative import declarative_base
import uuid
from datetime import datetime

Base = declarative_base()


class UUID(TypeDecorator):
    """
    Platform-independent UUID type.
    Uses PostgreSQL's UUID type when available,
    otherwise uses CHAR(36), storing as string.
    """
    impl = String
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PostgreSQLUUID())
        else:
            return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return str(value)
            else:
                return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            return value


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

    id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
