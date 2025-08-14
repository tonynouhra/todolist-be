"""
File model for file attachments.
"""

from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModel


class File(BaseModel):
    """
    Represents a file attachment entity in the application.
    """
    __tablename__ = "files"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    todo_id = Column(UUID(as_uuid=True), ForeignKey("todos.id"))
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    mime_type = Column(String(100))
    content_type = Column(String(100))  # Alias for mime_type for AI service compatibility

    # Relationships
    user = relationship("User", back_populates="files")
    todo = relationship("Todo", back_populates="files")