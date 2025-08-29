"""
File model for file attachments.
"""

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .base import UUID, BaseModel


class File(BaseModel):
    """
    Represents a file attachment entity in the application.
    """

    __tablename__ = "files"

    user_id = Column(UUID(), ForeignKey("users.id"), nullable=False)
    # Note: todo_id is not a direct foreign key anymore due to partitioning
    # We'll handle the relationship through application logic
    todo_id = Column(UUID())  # Removed ForeignKey constraint
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer)
    mime_type = Column(String(100))
    content_type = Column(String(100))  # Alias for mime_type for AI service compatibility

    # Relationships
    user = relationship("User", back_populates="files")

    # Note: todo relationship removed due to partitioned structure
    # Files are now linked to active todos through application logic
