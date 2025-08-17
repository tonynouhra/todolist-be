"""
Migration: 004_update_application_models.py
Purpose: Update SQLAlchemy models to support partitioned table structure
Author: Database Scaling Implementation
Date: 2025-01-XX

This file contains the new model definitions for the partitioned database structure.
Replace the existing models with these updated versions.
"""

from sqlalchemy import Column, String, Text, Integer, DateTime, Boolean, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func
from models.base import BaseModel
import uuid


# ====================================================================
# UPDATED TODO MODELS FOR PARTITIONED STRUCTURE
# ====================================================================

class TodoActive(BaseModel):
    """
    Active todos model for partitioned table (status: todo, in_progress)
    
    This model represents todos that are currently being worked on.
    Partitioned by user_id for optimal query performance.
    """
    __tablename__ = "todos_active"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"))
    parent_todo_id = Column(UUID(as_uuid=True))  # Self-reference within same partition
    
    title = Column(String(500), nullable=False)
    description = Column(Text)
    status = Column(String(20), default="todo")
    priority = Column(Integer, default=3)
    due_date = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    ai_generated = Column(Boolean, default=False)
    depth = Column(Integer, default=0)  # New field for hierarchy depth
    
    # Relationships
    user = relationship("User", back_populates="active_todos")
    project = relationship("Project", back_populates="active_todos")
    files = relationship("File", back_populates="todo_active")
    ai_interactions = relationship("AITodoInteraction", back_populates="todo_active")
    
    # Table constraints
    __table_args__ = (
        CheckConstraint("status IN ('todo', 'in_progress', 'done')", name="check_status"),
        CheckConstraint("priority BETWEEN 1 AND 5", name="check_priority"),
        CheckConstraint("depth <= 10", name="check_max_depth"),
        CheckConstraint(
            "(status = 'done' AND completed_at IS NOT NULL) OR (status != 'done')",
            name="check_completed_at_when_done"
        ),
    )
    
    def __repr__(self) -> str:
        return f"<TodoActive(id={self.id}, title='{self.title[:30]}...', status='{self.status}')>"
    
    def is_completed(self) -> bool:
        """Check if the todo is completed."""
        return self.status == "done"
    
    def has_subtasks(self) -> bool:
        """Check if the todo has subtasks (needs custom query due to partitioning)."""
        # This would need to be implemented in the service layer
        return False
    
    def is_overdue(self) -> bool:
        """Check if the todo is overdue."""
        from datetime import datetime, timezone
        return (
            self.due_date is not None 
            and self.due_date < datetime.now(timezone.utc) 
            and not self.is_completed()
        )


class TodoArchived(BaseModel):
    """
    Archived todos model for completed todos
    
    This model stores completed todos that have been archived.
    Partitioned by archived_at date for efficient time-based queries.
    """
    __tablename__ = "todos_archived"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"))
    parent_todo_id = Column(UUID(as_uuid=True))  # Reference to archived parent
    
    title = Column(String(500), nullable=False)
    description = Column(Text)
    status = Column(String(20), nullable=False)
    priority = Column(Integer)
    due_date = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    ai_generated = Column(Boolean)
    depth = Column(Integer)
    
    archived_at = Column(DateTime(timezone=True), default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="archived_todos")
    project = relationship("Project", back_populates="archived_todos")
    
    def __repr__(self) -> str:
        return f"<TodoArchived(id={self.id}, title='{self.title[:30]}...', archived_at='{self.archived_at}')>"


class AITodoInteraction(BaseModel):
    """
    AI interactions separated from main todos table for better performance
    
    This model stores AI interaction history without cluttering the main todos table.
    Partitioned by user_id for efficient user-based queries.
    """
    __tablename__ = "ai_todo_interactions"
    
    todo_id = Column(UUID(as_uuid=True), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    interaction_type = Column(String(50), nullable=False)
    prompt = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    subtasks_generated = Column(Integer, default=0)
    model_used = Column(String(100))
    
    # Relationships
    user = relationship("User", back_populates="ai_interactions")
    todo_active = relationship("TodoActive", back_populates="ai_interactions")
    
    def __repr__(self) -> str:
        return f"<AITodoInteraction(id={self.id}, type='{self.interaction_type}', todo_id={self.todo_id})>"


# ====================================================================
# COMPATIBILITY LAYER (OPTIONAL)
# ====================================================================

class Todo(BaseModel):
    """
    Compatibility layer that provides a unified interface to both active and archived todos.
    
    This is a virtual model that doesn't correspond to a real table.
    Use TodoService methods to interact with the actual partitioned tables.
    """
    # This model is for backward compatibility only
    # All actual database operations should use TodoActive and TodoArchived
    
    @classmethod
    def from_active(cls, active_todo: TodoActive):
        """Create a Todo instance from TodoActive"""
        return cls(
            id=active_todo.id,
            user_id=active_todo.user_id,
            project_id=active_todo.project_id,
            parent_todo_id=active_todo.parent_todo_id,
            title=active_todo.title,
            description=active_todo.description,
            status=active_todo.status,
            priority=active_todo.priority,
            due_date=active_todo.due_date,
            completed_at=active_todo.completed_at,
            ai_generated=active_todo.ai_generated,
            depth=active_todo.depth,
            created_at=active_todo.created_at,
            updated_at=active_todo.updated_at
        )
    
    @classmethod
    def from_archived(cls, archived_todo: TodoArchived):
        """Create a Todo instance from TodoArchived"""
        return cls(
            id=archived_todo.id,
            user_id=archived_todo.user_id,
            project_id=archived_todo.project_id,
            parent_todo_id=archived_todo.parent_todo_id,
            title=archived_todo.title,
            description=archived_todo.description,
            status=archived_todo.status,
            priority=archived_todo.priority,
            due_date=archived_todo.due_date,
            completed_at=archived_todo.completed_at,
            ai_generated=archived_todo.ai_generated,
            depth=archived_todo.depth,
            created_at=archived_todo.created_at,
            updated_at=archived_todo.updated_at
        )


# ====================================================================
# UPDATED USER MODEL TO SUPPORT NEW RELATIONSHIPS
# ====================================================================

# Add these relationships to your existing User model:
"""
class User(BaseModel):
    # ... existing fields ...
    
    # Updated relationships for partitioned structure
    active_todos = relationship("TodoActive", back_populates="user")
    archived_todos = relationship("TodoArchived", back_populates="user")
    ai_interactions = relationship("AITodoInteraction", back_populates="user")
    
    # Keep original todos relationship for backward compatibility during migration
    # todos = relationship("Todo", back_populates="user")  # Remove after migration
"""

# ====================================================================
# UPDATED PROJECT MODEL TO SUPPORT NEW RELATIONSHIPS  
# ====================================================================

# Add these relationships to your existing Project model:
"""
class Project(BaseModel):
    # ... existing fields ...
    
    # Updated relationships for partitioned structure
    active_todos = relationship("TodoActive", back_populates="project")
    archived_todos = relationship("TodoArchived", back_populates="project")
    
    # Keep original todos relationship for backward compatibility during migration
    # todos = relationship("Todo", back_populates="project")  # Remove after migration
"""

# ====================================================================
# UPDATED FILE MODEL TO SUPPORT NEW RELATIONSHIPS
# ====================================================================

# Update your existing File model:
"""
class File(BaseModel):
    # ... existing fields ...
    
    # Updated relationship for partitioned structure
    todo_active = relationship("TodoActive", back_populates="files")
    
    # Note: Archived todos don't need file relationships as files are for active work
"""

# ====================================================================
# MIGRATION HELPER FUNCTIONS
# ====================================================================

def get_all_user_todos(db_session, user_id: UUID, include_archived: bool = False):
    """
    Helper function to get all todos for a user from both active and archived tables.
    Use this instead of direct model queries during transition period.
    """
    from sqlalchemy.orm import Session
    from sqlalchemy import union_all
    
    # Get active todos
    active_query = db_session.query(TodoActive).filter(TodoActive.user_id == user_id)
    
    if not include_archived:
        return active_query.all()
    
    # Get archived todos and combine
    archived_query = db_session.query(TodoArchived).filter(TodoArchived.user_id == user_id)
    
    # Convert to unified format (you'll need to implement this based on your needs)
    active_todos = [Todo.from_active(t) for t in active_query.all()]
    archived_todos = [Todo.from_archived(t) for t in archived_query.all()]
    
    return active_todos + archived_todos


def create_todo_in_partition(db_session, todo_data: dict):
    """
    Helper function to create todos in the appropriate partition.
    """
    # Always create new todos in active table
    todo = TodoActive(**todo_data)
    db_session.add(todo)
    return todo


def move_todo_to_archive(db_session, todo_id: UUID):
    """
    Helper function to move completed todo from active to archive table.
    """
    # Get todo from active table
    todo = db_session.query(TodoActive).filter(TodoActive.id == todo_id).first()
    if not todo or todo.status != 'done':
        return False
    
    # Create archived version
    archived_todo = TodoArchived(
        id=todo.id,
        user_id=todo.user_id,
        project_id=todo.project_id,
        parent_todo_id=todo.parent_todo_id,
        title=todo.title,
        description=todo.description,
        status=todo.status,
        priority=todo.priority,
        due_date=todo.due_date,
        completed_at=todo.completed_at,
        ai_generated=todo.ai_generated,
        depth=todo.depth,
        created_at=todo.created_at,
        updated_at=todo.updated_at
    )
    
    # Add to archive and remove from active
    db_session.add(archived_todo)
    db_session.delete(todo)
    
    return True


# ====================================================================
# USAGE EXAMPLES
# ====================================================================

"""
# Example usage in your service layer:

class TodoService:
    async def get_user_todos(self, user_id: UUID, include_archived: bool = False):
        if include_archived:
            # Query both tables
            active = await self.db.execute(
                select(TodoActive).where(TodoActive.user_id == user_id)
            )
            archived = await self.db.execute(
                select(TodoArchived).where(TodoArchived.user_id == user_id)
            )
            return active.scalars().all() + archived.scalars().all()
        else:
            # Query only active
            result = await self.db.execute(
                select(TodoActive).where(TodoActive.user_id == user_id)
            )
            return result.scalars().all()
    
    async def create_todo(self, todo_data: TodoCreate, user_id: UUID):
        # Always create in active table
        todo = TodoActive(
            user_id=user_id,
            title=todo_data.title,
            description=todo_data.description,
            # ... other fields
        )
        self.db.add(todo)
        await self.db.commit()
        return todo
    
    async def complete_todo(self, todo_id: UUID, user_id: UUID):
        # Update in active table (automatic archival will happen via maintenance job)
        todo = await self.db.execute(
            select(TodoActive).where(
                TodoActive.id == todo_id,
                TodoActive.user_id == user_id
            )
        )
        todo = todo.scalar_one_or_none()
        if todo:
            todo.status = 'done'
            todo.completed_at = datetime.utcnow()
            await self.db.commit()
        return todo
"""

# ====================================================================
# MODEL REGISTRATION
# ====================================================================

# Make sure to import these models in your models/__init__.py:
"""
from .todo_partitioned import TodoActive, TodoArchived, AITodoInteraction

# Export for easy access
__all__ = [
    'TodoActive',
    'TodoArchived', 
    'AITodoInteraction',
    # ... other models
]
"""

print("Updated models created successfully!")
print("Next steps:")
print("1. Replace your existing Todo model with TodoActive")
print("2. Update your service layer to use the new models")
print("3. Update relationships in User and Project models")
print("4. Test the application with new partitioned structure")
print("5. Run maintenance jobs to archive old completed todos")