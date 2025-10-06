"""
Provides the User model for the application's database schema.

The User model establishes the attributes and relationships associated
with users in the system. It inherits common behaviors and attributes
from the `BaseModel`. This model also defines relationships with other
models like `Todo`, `Project`, and `File`.

Attributes
----------
clerk_user_id : sqlalchemy.Column
    Unique identifier for the user from an external clerk system.
email : sqlalchemy.Column
    The email address of the user, which must also be unique.
username : sqlalchemy.Column
    The optional username chosen by the user.
is_active : sqlalchemy.Column
    A boolean indicating if the user is active. Defaults to `True`.

Relationships
-------------
todos : sqlalchemy.orm.relationship
    Defines a one-to-many relationship with the `Todo` model. Supports
    cascading deletes for related objects.
projects : sqlalchemy.orm.relationship
    Defines a one-to-many relationship with the `Project` model. Supports
    cascading deletes for related objects.
files : sqlalchemy.orm.relationship
    Defines a one-to-many relationship with the `File` model. Supports
    cascading deletes for related objects.
"""

from sqlalchemy import Boolean, Column, String
from sqlalchemy.orm import relationship

from .base import BaseModel


class User(BaseModel):
    """
    Represents a user entity in the application.

    This class defines the structure of a `User`, including attributes
    such as an email, username, and whether the user is active. It also
    manages relationships with other entities like `Todo`, `Project`, and
    `File`.

    :ivar clerk_user_id: Unique identifier for the user provided by Clerk.
    :type clerk_user_id: str
    :ivar email: Email address of the user. It must be unique.
    :type email: str
    :ivar username: Username of the user. This is optional.
    :type username: str
    :ivar is_active: Indicates whether the user account is active.
    :type is_active: bool
    """

    __tablename__ = "users"

    clerk_user_id = Column(String(255), unique=True, nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    username = Column(String(100))
    is_active = Column(Boolean, default=True)

    # Relationships
    # Keep original todos relationship for backward compatibility during migration
    todos = relationship("Todo", back_populates="user", cascade="all, delete-orphan")

    # New partitioned relationships
    active_todos = relationship("TodoActive", back_populates="user", cascade="all, delete-orphan")
    archived_todos = relationship("TodoArchived", back_populates="user", cascade="all, delete-orphan")
    ai_interactions = relationship("AITodoInteraction", back_populates="user", cascade="all, delete-orphan")

    # Other relationships
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    files = relationship("File", back_populates="user", cascade="all, delete-orphan")
    settings = relationship("UserSettings", back_populates="user", cascade="all, delete-orphan", uselist=False)
    chat_conversations = relationship("ChatConversation", back_populates="user", cascade="all, delete-orphan")
    push_subscriptions = relationship("PushSubscription", back_populates="user", cascade="all, delete-orphan")
