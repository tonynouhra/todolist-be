# Project Structure for FastAPI Backend

"""
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Configuration management
│   ├── database.py             # Database connection and session
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py            # Dependencies (auth, db session)
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── auth.py        # Authentication endpoints
│   │       ├── todos.py       # Todo CRUD endpoints
│   │       ├── ai.py          # AI integration endpoints
│   │       ├── files.py       # File management endpoints
│   │       └── users.py       # User management endpoints
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py          # Core configuration
│   │   ├── security.py        # Security utilities
│   │   └── exceptions.py      # Custom exceptions
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py           # User SQLAlchemy model
│   │   ├── todo.py           # Todo SQLAlchemy model
│   │   ├── file.py           # File SQLAlchemy model
│   │   └── ai_interaction.py # AI interaction model
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── user.py           # User Pydantic schemas
│   │   ├── todo.py           # Todo Pydantic schemas
│   │   ├── file.py           # File Pydantic schemas
│   │   └── ai.py             # AI-related schemas
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth.py           # Clerk authentication service
│   │   ├── todo.py           # Todo business logic
│   │   ├── ai.py             # Gemini AI service
│   │   ├── file.py           # File storage service
│   │   └── notification.py   # WebSocket notifications
│   │
│   └── utils/
│       ├── __init__.py
│       ├── validators.py     # Custom validators
│       ├── helpers.py        # Helper functions
│       └── websocket.py      # WebSocket manager
│
├── migrations/                # Alembic migrations
│   ├── alembic.ini
│   └── versions/
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Test configuration
│   ├── test_auth.py
│   ├── test_todos.py
│   ├── test_ai.py
│   └── test_files.py
│
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── Dockerfile
└── docker-compose.yml
"""

# === main.py ===
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from app.api.v1 import auth, todos, ai, files, users
from app.core.config import settings
from app.database import engine, Base
from app.utils.websocket import manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await startup_event()
    yield
    # Shutdown
    await shutdown_event()

async def startup_event():
    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created")

async def shutdown_event():
    await manager.disconnect_all()
    print("Shutting down...")

app = FastAPI(
    title="AI Todo List API",
    description="Intelligent task management with AI assistance",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(todos.router, prefix="/api/v1/todos", tags=["Todos"])
app.include_router(ai.router, prefix="/api/v1/ai", tags=["AI"])
app.include_router(files.router, prefix="/api/v1/files", tags=["Files"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

# === config.py ===
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    
    # Authentication
    CLERK_SECRET_KEY: str
    CLERK_API_URL: str = "https://api.clerk.dev"
    
    # AI Service
    GEMINI_API_KEY: str
    
    # File Storage
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    S3_BUCKET_NAME: str
    S3_REGION: str = "us-east-1"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]
    
    # Limits
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB
    MAX_TODOS_PER_USER: int = 1000
    MAX_SUBTASKS_DEPTH: int = 5
    
    class Config:
        env_file = ".env"

settings = Settings()

# === models/todo.py ===
from sqlalchemy import Column, String, Text, Integer, DateTime, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime

from app.database import Base

class Todo(Base):
    __tablename__ = "todos"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"))
    parent_todo_id = Column(UUID(as_uuid=True), ForeignKey("todos.id"))
    
    title = Column(String(500), nullable=False)
    description = Column(Text)
    status = Column(String(20), default="todo")
    priority = Column(Integer, default=3)
    due_date = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)
    ai_generated = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="todos")
    project = relationship("Project", back_populates="todos")
    subtasks = relationship("Todo", backref="parent", remote_side=[id])
    files = relationship("File", back_populates="todo")
    ai_interactions = relationship("AIInteraction", back_populates="todo")

# === schemas/todo.py ===
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID

class TodoBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    status: str = Field(default="todo", regex="^(todo|in_progress|done)$")
    priority: int = Field(default=3, ge=1, le=5)
    due_date: Optional[datetime] = None
    project_id: Optional[UUID] = None
    parent_todo_id: Optional[UUID] = None

class TodoCreate(TodoBase):
    generate_subtasks: bool = False
    
class TodoUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    status: Optional[str] = Field(None, regex="^(todo|in_progress|done)$")
    priority: Optional[int] = Field(None, ge=1, le=5)
    due_date: Optional[datetime] = None
    project_id: Optional[UUID] = None

class TodoResponse(TodoBase):
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    ai_generated: bool
    subtasks: List['TodoResponse'] = []
    
    class Config:
        from_attributes = True

# === services/ai.py ===
import google.generativeai as genai
from typing import List, Dict
import json

from app.core.config import settings
from app.schemas.todo import TodoBase

class AIService:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-pro')
    
    async def generate_subtasks(self, todo_title: str, todo_description: str) -> List[Dict]:
        """Generate subtasks for a given todo using Gemini AI"""
        
        prompt = f"""
        Given the following task, generate a list of subtasks that would help complete it.
        
        Task Title: {todo_title}
        Task Description: {todo_description or "No description provided"}
        
        Generate 3-7 relevant subtasks. Return the response as a JSON array with this structure:
        [
            {{
                "title": "Subtask title",
                "description": "Brief description of what needs to be done",
                "priority": 1-5 (where 1 is highest),
                "estimated_hours": estimated time in hours
            }}
        ]
        
        Make the subtasks specific, actionable, and logically ordered.
        """
        
        try:
            response = await self.model.generate_content_async(prompt)
            # Parse the JSON response
            subtasks_data = json.loads(response.text)
            
            # Convert to our schema
            subtasks = []
            for task in subtasks_data:
                subtasks.append({
                    "title": task["title"],
                    "description": task.get("description", ""),
                    "priority": task.get("priority", 3),
                    "status": "todo",
                    "ai_generated": True
                })
            
            return subtasks
            
        except Exception as e:
            print(f"Error generating subtasks: {e}")
            return []
    
    async def analyze_file(self, file_content: bytes, file_type: str) -> Dict:
        """Analyze uploaded file content using Gemini"""
        
        # Implementation depends on file type
        # For now, return a basic analysis
        return {
            "summary": "File analysis completed",
            "key_points": [],
            "suggestions": []
        }

# === api/v1/todos.py ===
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.schemas.todo import TodoCreate, TodoUpdate, TodoResponse
from app.services.todo import TodoService
from app.services.ai import AIService

router = APIRouter()

@router.post("/", response_model=TodoResponse)
async def create_todo(
    todo: TodoCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new todo with optional AI-generated subtasks"""
    
    todo_service = TodoService(db)
    ai_service = AIService()
    
    # Create the main todo
    new_todo = await todo_service.create_todo(
        user_id=current_user.id,
        todo_data=todo.dict(exclude={"generate_subtasks"})
    )
    
    # Generate subtasks if requested
    if todo.generate_subtasks:
        subtasks = await ai_service.generate_subtasks(
            todo.title,
            todo.description
        )
        
        for subtask_data in subtasks:
            subtask_data["parent_todo_id"] = new_todo.id
            await todo_service.create_todo(
                user_id=current_user.id,
                todo_data=subtask_data
            )
    
    # Fetch the todo with subtasks
    return await todo_service.get_todo_with_subtasks(new_todo.id)

@router.get("/", response_model=List[TodoResponse])
async def get_todos(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all todos for the current user"""
    
    todo_service = TodoService(db)
    return await todo_service.get_user_todos(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        status=status
    )

@router.get("/{todo_id}", response_model=TodoResponse)
async def get_todo(
    todo_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get a specific todo by ID"""
    
    todo_service = TodoService(db)
    todo = await todo_service.get_todo_with_subtasks(todo_id)
    
    if not todo or todo.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found"
        )
    
    return todo

@router.put("/{todo_id}", response_model=TodoResponse)
async def update_todo(
    todo_id: UUID,
    todo_update: TodoUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update a todo"""
    
    todo_service = TodoService(db)
    updated_todo = await todo_service.update_todo(
        todo_id=todo_id,
        user_id=current_user.id,
        todo_data=todo_update.dict(exclude_unset=True)
    )
    
    if not updated_todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found"
        )
    
    return updated_todo

@router.delete("/{todo_id}")
async def delete_todo(
    todo_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Delete a todo and all its subtasks"""
    
    todo_service = TodoService(db)
    success = await todo_service.delete_todo(
        todo_id=todo_id,
        user_id=current_user.id
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Todo not found"
        )
    
    return {"message": "Todo deleted successfully"}