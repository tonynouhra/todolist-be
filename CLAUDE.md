# AI Todo List Project - Claude Memory

## Project Overview

This is an intelligent task management system that leverages AI capabilities to help users organize, break down, and complete their tasks efficiently. The system supports hierarchical task structures with AI-assisted sub-task generation and file interaction capabilities.

### Key Features
- Hierarchical todo structure (main tasks and sub-tasks)
- AI-powered sub-task generation using Google Gemini
- File upload and AI interaction capabilities
- Multi-platform support (Web, iOS, Android)
- Real-time status tracking with WebSocket
- Secure authentication via Clerk
- Cloud-based PostgreSQL database with Neon

## Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Database**: Neon (PostgreSQL) with AsyncPG
- **ORM**: SQLAlchemy 2.0 (async)
- **Authentication**: Clerk (JWT-based)
- **AI Service**: Google Gemini API
- **File Storage**: AWS S3 / CloudFlare R2
- **Cache**: Redis
- **Background Tasks**: Celery
- **Migration**: Alembic

### Frontend
- **Web**: React/Vue.js with TypeScript
- **Mobile iOS**: Swift + SwiftUI
- **Mobile Android**: Kotlin + Jetpack Compose
- **State Management**: Zustand (React) / Pinia (Vue)
- **Styling**: Tailwind CSS
- **HTTP Client**: Axios with React Query

### Infrastructure
- **Container**: Docker
- **CI/CD**: GitHub Actions
- **Monitoring**: Prometheus + Grafana
- **Error Tracking**: Sentry
- **Deployment**: Kubernetes (optional)

## Project Structure

```
app/
├── main.py
├── database.py
├── core/
│   ├── config.py
│   ├── dependencies.py
│   └── security.py
├── models/           # All SQLAlchemy models
│   ├── __init__.py
│   ├── base.py      # Base model class
│   ├── user.py
│   ├── todo.py
│   ├── project.py
│   ├── file.py
│   └── ai_interaction.py
├── schemas/          # All Pydantic schemas
│   ├── __init__.py
│   ├── base.py      # Base schema classes
│   ├── user.py
│   ├── todo.py
│   ├── project.py
│   ├── file.py
│   └── ai.py
├── exceptions/       # All custom exceptions
│   ├── __init__.py
│   ├── base.py      # Base exception classes
│   ├── user.py
│   ├── todo.py
│   └── ai.py
├── domains/          # Business logic & controllers
│   ├── user/
│   │   ├── __init__.py
│   │   ├── controller.py
│   │   └── service.py
│   ├── todo/
│   │   ├── __init__.py
│   │   ├── controller.py
│   │   └── service.py
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── controller.py
│   │   └── service.py
│   └── file/
│       ├── __init__.py
│       ├── controller.py
│       └── service.py
└── shared/           # Shared utilities
    ├── utils.py
    ├── pagination.py
    └── websocket.py
```

## Database Schema

### Core Tables
- **users**: User profiles (synced with Clerk)
- **projects**: Project organization
- **todos**: Hierarchical task structure
- **files**: File attachments with AI analysis
- **ai_interactions**: AI conversation history

### Key Relationships
- Users can have multiple projects and todos
- Todos can have parent-child relationships (unlimited nesting)
- Files can be attached to todos
- AI interactions are linked to todos and users

## Core Models and Patterns

### Todo Model Pattern
```python
class Todo(Base):
    __tablename__ = "todos"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    parent_todo_id = Column(UUID(as_uuid=True), ForeignKey("todos.id"))
    
    title = Column(String(500), nullable=False)
    description = Column(Text)
    status = Column(String(20), default="todo")  # todo, in_progress, done
    priority = Column(Integer, default=3)  # 1-5 scale
    due_date = Column(DateTime)
    ai_generated = Column(Boolean, default=False)
    
    # Self-referencing relationship for hierarchical structure
    subtasks = relationship("Todo", backref="parent", remote_side=[id])
```

### API Response Pattern
```python
{
    "status": "success|error",
    "data": {},
    "message": "string",
    "timestamp": "ISO 8601",
    "request_id": "uuid"
}
```

### Authentication Pattern
- All API endpoints require valid JWT token from Clerk
- Use `get_current_user` dependency for user context
- Implement rate limiting per user (100 req/min)

## AI Integration Patterns

### Sub-task Generation
```python
async def generate_subtasks(self, todo_title: str, todo_description: str) -> List[Dict]:
    prompt = f"""
    Given the following task, generate a list of subtasks that would help complete it.
    
    Task Title: {todo_title}
    Task Description: {todo_description or "No description provided"}
    
    Generate 3-7 relevant subtasks. Return as JSON array...
    """
    
    response = await self.model.generate_content_async(prompt)
    return json.loads(response.text)
```

### Error Handling for AI
- Implement retry logic for API failures
- Graceful degradation when AI service is unavailable
- Token usage tracking and quota management

## API Endpoints Structure

### Authentication
- `POST /api/auth/login` - Login with Clerk
- `GET /api/auth/me` - Get current user

### Todos
- `GET /api/todos` - List todos with filters
- `POST /api/todos` - Create todo (with optional AI subtask generation)
- `GET /api/todos/{id}` - Get todo with subtasks
- `PUT /api/todos/{id}` - Update todo
- `DELETE /api/todos/{id}` - Delete todo and subtasks

### AI Features
- `POST /api/ai/generate-subtasks` - Generate subtasks
- `POST /api/ai/analyze-file` - Analyze uploaded file

### Files
- `POST /api/files/upload` - Upload file with validation
- `GET /api/files/{id}` - Download file
- `DELETE /api/files/{id}` - Delete file

## Development Guidelines

### Code Style
- Use async/await for all database operations
- Follow FastAPI dependency injection patterns
- Implement proper error handling with custom exceptions
- Use Pydantic for request/response validation
- Write comprehensive docstrings

### Database Patterns
- Always use UUIDs for primary keys
- Implement soft deletes where appropriate
- Use database indexes for performance
- Handle cascading deletes properly
- Implement proper foreign key constraints

### Testing Strategy
- Unit tests for services layer
- Integration tests for API endpoints
- Mock external services (Clerk, Gemini)
- Test AI error scenarios
- Performance testing for file uploads

### Security Considerations
- Validate file types and sizes
- Sanitize AI prompts and responses
- Implement rate limiting
- Use environment variables for secrets
- Follow OWASP security guidelines

## Configuration Management

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql+asyncpg://...

# Authentication
CLERK_SECRET_KEY=sk_...
CLERK_API_URL=https://api.clerk.dev

# AI Service
GEMINI_API_KEY=...

# File Storage
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
S3_BUCKET_NAME=...

# Redis
REDIS_URL=redis://localhost:6379

# Limits
MAX_FILE_SIZE=52428800  # 50MB
MAX_TODOS_PER_USER=1000
```

## Common Workflows

### Creating Todo with AI Subtasks
1. Validate user input
2. Create main todo in database
3. If AI generation requested, call Gemini API
4. Parse AI response and create subtasks
5. Return todo with generated subtasks
6. Send WebSocket notification

### File Upload and Analysis
1. Validate file type and size
2. Upload to S3/CloudFlare storage
3. Store metadata in database
4. Queue AI analysis job
5. Process with Gemini API
6. Store analysis results
7. Notify user of completion

## Performance Considerations

### Database Optimization
- Use connection pooling
- Implement query pagination
- Index frequently queried columns
- Use database-level constraints
- Monitor slow queries

### Caching Strategy
- Cache user sessions in Redis
- Cache frequently accessed todos
- Implement CDN for static files
- Use HTTP caching headers

### Scalability Patterns
- Implement background job processing
- Use async operations for I/O
- Design for horizontal scaling
- Monitor resource usage

## Error Handling Patterns

### Custom Exceptions
```python
class TodoNotFoundError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=404,
            detail="Todo not found"
        )

class AIServiceUnavailableError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=503,
            detail="AI service temporarily unavailable"
        )
```

### Graceful Degradation
- Continue without AI when service fails
- Provide fallback responses
- Log errors for monitoring
- Maintain user experience

## Deployment Configuration

### Docker Setup
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Health Checks
```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "database": await check_database(),
        "redis": await check_redis(),
        "ai_service": await check_ai_service()
    }
```

## Monitoring and Observability

### Logging
- Use structured JSON logging
- Log all AI interactions
- Track user actions
- Monitor performance metrics

### Metrics to Track
- API response times
- AI generation success rate
- File upload metrics
- User engagement
- Error rates

## Development Phases

### Current Phase: Sprint 0-1 (Setup & Core Backend)
- Repository setup and CI/CD
- Database schema implementation
- Authentication integration
- Basic CRUD operations

### Next Steps
- AI service integration
- File upload functionality
- Frontend development
- Mobile app development
- Testing and optimization

## Important Notes

### AI Usage Guidelines
- Implement prompt injection protection
- Monitor token usage and costs
- Handle API rate limits gracefully
- Provide user feedback for AI operations

### Data Privacy
- User data is encrypted at rest
- Comply with data protection regulations
- Implement proper access controls
- Regular security audits

### File Handling
- Maximum file size: 50MB
- Supported types: images, documents, text files
- Virus scanning before processing
- Automatic cleanup of temporary files

This memory file provides context for understanding the project structure, patterns, and conventions used throughout the AI Todo List application.