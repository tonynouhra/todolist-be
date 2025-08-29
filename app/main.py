"""AI Todo List API - Main Application Module.

This module initializes the FastAPI application with proper configuration,
middleware, routing, and lifecycle management for the AI-powered todo system.
"""

import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

# Add the project root to Python path if running directly
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.database import engine, get_db
from models import Base


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Manage application lifecycle events."""
    # Startup
    print("🚀 Starting AI Todo List API...")

    # Development mode: Auto-create tables if they don't exist
    # Production: Use Alembic migrations (alembic upgrade head)
    if settings.environment == "development":
        print("📝 Development mode: Creating/updating database tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Database tables created/verified")
    else:
        print("🏭 Production mode: Use 'alembic upgrade head' to manage database schema")
        print("✅ Application started")

    yield

    # Shutdown
    print("🛑 Shutting down AI Todo List API...")
    await engine.dispose()
    print("✅ Database connections closed")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="AI Todo List API",
        description="Intelligent task management system with AI-powered sub-task generation",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.environment == "development" else None,
        redoc_url="/redoc" if settings.environment == "development" else None,
    )

    # Add middleware
    setup_middleware(app)

    # Add exception handlers
    setup_exception_handlers(app)

    # Include routers
    setup_routers(app)

    return app


def setup_middleware(app: FastAPI):
    """Configure application middleware."""
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request ID middleware
    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


def setup_exception_handlers(app: FastAPI):
    """Configure global exception handlers."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        # Handle custom exceptions that have structured detail
        if isinstance(exc.detail, dict) and "message" in exc.detail:
            message = exc.detail["message"]
            error_code = exc.detail.get("error_code", "HTTP_ERROR")
            details = exc.detail.get("details")
        else:
            message = str(exc.detail) if exc.detail else "An error occurred"
            error_code = "HTTP_ERROR"
            details = None

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "status": "error",
                "message": message,
                "error_code": error_code,
                "details": details,
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        # Convert errors to JSON-serializable format
        errors = []
        for error in exc.errors():
            error_dict = {
                "loc": error.get("loc", []),
                "msg": str(error.get("msg", "Validation error")),
                "type": error.get("type", "value_error"),
            }
            # Handle custom input if present
            if "input" in error:
                error_dict["input"] = str(error["input"])
            errors.append(error_dict)

        return JSONResponse(
            status_code=422,
            content={
                "status": "error",
                "message": "Validation error",
                "details": errors,
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": getattr(request.state, "request_id", None),
            },
        )


def setup_routers(app: FastAPI):
    """Configure application routers."""
    # Import routers
    from app.domains.ai.controller import router as ai_router
    from app.domains.project.controller import router as project_router
    from app.domains.todo.controller import router as todo_router
    from app.domains.user.controller import router as user_router

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        """Comprehensive health check endpoint."""
        try:
            # Check database connection
            db_status = "healthy"
            try:
                db = next(get_db())
                await db.execute("SELECT 1")
                await db.close()
            except Exception:
                db_status = "unhealthy"

            # Check AI service status
            ai_status = "not_configured"
            if settings.has_ai_enabled:
                try:
                    from app.domains.ai.service import AIService

                    ai_service = AIService(next(get_db()))
                    status_info = await ai_service.get_service_status()
                    ai_status = "healthy" if status_info.service_available else "unhealthy"
                except Exception:
                    ai_status = "unhealthy"

            return {
                "status": (
                    "healthy"
                    if db_status == "healthy" and (ai_status in ["healthy", "not_configured"])
                    else "degraded"
                ),
                "version": "1.0.0",
                "environment": settings.environment,
                "timestamp": datetime.utcnow().isoformat(),
                "services": {
                    "database": db_status,
                    "ai_service": ai_status,
                },
            }
        except Exception as e:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "message": f"Health check failed: {str(e)}",
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

    @app.get("/")
    async def root():
        """Root endpoint with API information."""
        return {
            "name": "AI Todo List API",
            "version": "1.0.0",
            "description": "Intelligent task management with AI assistance",
            "docs_url": "/docs" if settings.environment == "development" else None,
        }

    # Include domain routers
    app.include_router(user_router)
    app.include_router(todo_router)
    app.include_router(project_router)
    app.include_router(ai_router)


# Create the application instance
app = create_app()


def main():
    """Entry point for running the application directly."""
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,  # Use configurable host instead of hardcoded 0.0.0.0
        port=settings.port,  # Use configurable port instead of hardcoded 8000
        reload=settings.environment == "development",
        log_level="info",
    )


if __name__ == "__main__":
    main()
