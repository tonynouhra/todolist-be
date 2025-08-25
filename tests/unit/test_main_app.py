"""
Unit tests for Main Application module.

This module contains comprehensive unit tests for the main FastAPI application,
middleware, exception handlers, and application lifecycle.
"""

import json
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from httpx import AsyncClient
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.main import (
    app,
    create_app,
    setup_exception_handlers,
    setup_middleware,
    setup_routers,
)


class TestAppCreation:
    """Test cases for FastAPI application creation."""

    def test_create_app_returns_fastapi_instance(self):
        """Test that create_app returns a FastAPI instance."""
        test_app = create_app()
        
        assert test_app.title == "AI Todo List API"
        assert test_app.description == "Intelligent task management system with AI-powered sub-task generation"
        assert test_app.version == "1.0.0"

    def test_app_docs_configuration_development(self):
        """Test docs configuration in development mode."""
        with patch('app.main.settings') as mock_settings:
            mock_settings.environment = "development"
            
            test_app = create_app()
            
            # In development, docs should be available
            assert test_app.docs_url == "/docs"
            assert test_app.redoc_url == "/redoc"

    def test_app_docs_configuration_production(self):
        """Test docs configuration in production mode."""
        with patch('app.main.settings') as mock_settings:
            mock_settings.environment = "production"
            
            test_app = create_app()
            
            # In production, docs should be disabled
            assert test_app.docs_url is None
            assert test_app.redoc_url is None

    def test_app_components_setup(self):
        """Test that all app components are set up correctly."""
        with patch('app.main.setup_middleware') as mock_middleware:
            with patch('app.main.setup_exception_handlers') as mock_handlers:
                with patch('app.main.setup_routers') as mock_routers:
                    
                    test_app = create_app()
                    
                    mock_middleware.assert_called_once_with(test_app)
                    mock_handlers.assert_called_once_with(test_app)
                    mock_routers.assert_called_once_with(test_app)


class TestMiddleware:
    """Test cases for application middleware."""

    @pytest.mark.asyncio
    async def test_cors_middleware_configuration(self):
        """Test CORS middleware is configured correctly."""
        with TestClient(app) as client:
            # Test preflight request
            response = client.options(
                "/api/todos/",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Content-Type,Authorization"
                }
            )
            
            # Should allow CORS
            assert "access-control-allow-origin" in response.headers

    @pytest.mark.asyncio
    async def test_request_id_middleware(self, client: AsyncClient):
        """Test request ID middleware adds request ID header."""
        response = await client.get("/health")
        
        assert "X-Request-ID" in response.headers
        # Should be a valid UUID
        request_id = response.headers["X-Request-ID"]
        assert uuid.UUID(request_id)  # Will raise if not valid UUID

    @pytest.mark.asyncio
    async def test_request_id_middleware_different_requests(self, client: AsyncClient):
        """Test that different requests get different request IDs."""
        response1 = await client.get("/health")
        response2 = await client.get("/health")
        
        request_id1 = response1.headers["X-Request-ID"]
        request_id2 = response2.headers["X-Request-ID"]
        
        assert request_id1 != request_id2

    def test_setup_middleware_called_during_app_creation(self):
        """Test that setup_middleware is called during app creation."""
        mock_app = MagicMock()
        
        setup_middleware(mock_app)
        
        # Should add CORS middleware
        mock_app.add_middleware.assert_called()
        
        # Should add request ID middleware
        mock_app.middleware.assert_called_with("http")


class TestExceptionHandlers:
    """Test cases for application exception handlers."""

    @pytest.mark.asyncio
    async def test_http_exception_handler(self, client: AsyncClient):
        """Test HTTP exception handler."""
        # Trigger a 404 by accessing non-existent endpoint
        response = await client.get("/nonexistent-endpoint")
        
        assert response.status_code == 404
        data = response.json()
        
        assert data["status"] == "error"
        assert "message" in data
        assert "timestamp" in data
        # Request ID should be included if middleware is working
        assert "request_id" in data

    @pytest.mark.asyncio
    async def test_validation_exception_handler(self, client: AsyncClient):
        """Test validation exception handler."""
        # Send invalid data to trigger validation error
        response = await client.post(
            "/api/todos/",
            json={"invalid_field": "value"},  # Missing required fields
            headers={"Authorization": "Bearer fake_token"}
        )
        
        assert response.status_code == 422
        data = response.json()
        
        assert data["status"] == "error"
        assert data["message"] == "Validation error"
        assert "details" in data
        assert "timestamp" in data

    def test_setup_exception_handlers_registration(self):
        """Test that exception handlers are properly registered."""
        mock_app = MagicMock()
        
        setup_exception_handlers(mock_app)
        
        # Should register exception handlers
        assert mock_app.exception_handler.call_count >= 2
        
        # Check that both StarletteHTTPException and RequestValidationError handlers are registered
        call_args_list = mock_app.exception_handler.call_args_list
        exception_types = [call[0][0] for call in call_args_list]
        
        assert StarletteHTTPException in exception_types
        assert RequestValidationError in exception_types


class TestHealthEndpoint:
    """Test cases for health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check_success(self, client: AsyncClient):
        """Test successful health check."""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] in ["healthy", "degraded"]
        assert data["version"] == "1.0.0"
        assert "environment" in data
        assert "timestamp" in data
        assert "services" in data
        assert "database" in data["services"]

    @pytest.mark.asyncio
    async def test_health_check_database_status(self, client: AsyncClient):
        """Test health check database status."""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Database status should be reported
        assert data["services"]["database"] in ["healthy", "unhealthy"]

    @pytest.mark.asyncio
    async def test_health_check_ai_service_status(self, client: AsyncClient):
        """Test health check AI service status."""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # AI service status should be reported
        assert data["services"]["ai_service"] in ["healthy", "unhealthy", "not_configured"]

    @pytest.mark.asyncio
    async def test_health_check_with_database_error(self, client: AsyncClient):
        """Test health check when database is unhealthy."""
        with patch('app.main.get_db') as mock_get_db:
            mock_db = AsyncMock()
            mock_db.execute.side_effect = Exception("Database connection failed")
            mock_get_db.return_value = mock_db
            
            response = await client.get("/health")
            
            # Should still return 200 but with degraded status
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "degraded"
            assert data["services"]["database"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_health_check_ai_service_error(self, client: AsyncClient):
        """Test health check when AI service check fails."""
        with patch('app.main.settings') as mock_settings:
            mock_settings.has_ai_enabled = True
            
            with patch('app.domains.ai.service.AIService') as mock_ai_service:
                mock_ai_service.return_value.get_service_status.side_effect = Exception("AI service error")
                
                response = await client.get("/health")
                
                assert response.status_code == 200
                data = response.json()
                assert data["services"]["ai_service"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_health_check_complete_failure(self, client: AsyncClient):
        """Test health check when everything fails."""
        with patch('app.main.get_db') as mock_get_db:
            mock_get_db.side_effect = Exception("Complete failure")
            
            response = await client.get("/health")
            
            # Should return 503 for complete failure
            assert response.status_code == 503
            data = response.json()
            assert data["status"] == "unhealthy"
            assert "Health check failed" in data["message"]


class TestRootEndpoint:
    """Test cases for root endpoint."""

    @pytest.mark.asyncio
    async def test_root_endpoint_development(self, client: AsyncClient):
        """Test root endpoint in development mode."""
        with patch('app.main.settings') as mock_settings:
            mock_settings.environment = "development"
            
            response = await client.get("/")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["name"] == "AI Todo List API"
            assert data["version"] == "1.0.0"
            assert data["description"] == "Intelligent task management with AI assistance"
            assert data["docs_url"] == "/docs"

    @pytest.mark.asyncio
    async def test_root_endpoint_production(self, client: AsyncClient):
        """Test root endpoint in production mode."""
        with patch('app.main.settings') as mock_settings:
            mock_settings.environment = "production"
            
            response = await client.get("/")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["name"] == "AI Todo List API"
            assert data["version"] == "1.0.0"
            assert data["docs_url"] is None


class TestRouterSetup:
    """Test cases for router setup."""

    def test_setup_routers_includes_all_domains(self):
        """Test that all domain routers are included."""
        mock_app = MagicMock()
        
        with patch('app.domains.user.controller.router') as mock_user_router:
            with patch('app.domains.todo.controller.router') as mock_todo_router:
                with patch('app.domains.project.controller.router') as mock_project_router:
                    with patch('app.domains.ai.controller.router') as mock_ai_router:
                        
                        setup_routers(mock_app)
                        
                        # All routers should be included
                        mock_app.include_router.assert_any_call(mock_user_router)
                        mock_app.include_router.assert_any_call(mock_todo_router)
                        mock_app.include_router.assert_any_call(mock_project_router)
                        mock_app.include_router.assert_any_call(mock_ai_router)

    @pytest.mark.asyncio
    async def test_router_endpoints_accessible(self, client: AsyncClient):
        """Test that router endpoints are accessible."""
        # Test that main domain endpoints exist (will return 401 without auth, but that's expected)
        
        # User endpoints
        response = await client.get("/api/users/profile")
        assert response.status_code in [200, 401, 422]  # Any of these is fine - means endpoint exists
        
        # Todo endpoints  
        response = await client.get("/api/todos/")
        assert response.status_code in [200, 401, 422]
        
        # AI endpoints
        response = await client.get("/api/ai/status")
        assert response.status_code in [200, 401, 422]


class TestApplicationLifespan:
    """Test cases for application lifespan management."""

    @pytest.mark.asyncio
    async def test_lifespan_startup_development(self):
        """Test application startup in development mode."""
        with patch('app.main.settings') as mock_settings:
            mock_settings.environment = "development"
            
            with patch('app.main.engine') as mock_engine:
                mock_conn = AsyncMock()
                mock_engine.begin.return_value.__aenter__.return_value = mock_conn
                
                # Test lifespan context manager
                from app.main import lifespan
                
                test_app = MagicMock()
                async with lifespan(test_app):
                    # During startup, tables should be created in development
                    mock_engine.begin.assert_called_once()
                
                # During shutdown, engine should be disposed
                mock_engine.dispose.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_startup_production(self):
        """Test application startup in production mode."""
        with patch('app.main.settings') as mock_settings:
            mock_settings.environment = "production"
            
            with patch('app.main.engine') as mock_engine:
                from app.main import lifespan
                
                test_app = MagicMock()
                async with lifespan(test_app):
                    # In production, tables should NOT be auto-created
                    mock_engine.begin.assert_not_called()
                
                # Engine should still be disposed on shutdown
                mock_engine.dispose.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_exception_handling(self):
        """Test lifespan exception handling."""
        with patch('app.main.engine') as mock_engine:
            mock_engine.dispose.side_effect = Exception("Disposal error")
            
            from app.main import lifespan
            
            test_app = MagicMock()
            
            # Should not raise exception even if disposal fails
            try:
                async with lifespan(test_app):
                    pass
            except Exception:
                pytest.fail("Lifespan should handle disposal exceptions gracefully")


class TestApplicationConfiguration:
    """Test cases for application configuration."""

    def test_app_instance_is_configured(self):
        """Test that the main app instance is properly configured."""
        assert app.title == "AI Todo List API"
        assert app.version == "1.0.0"
        
        # Should have routes registered
        routes = [route.path for route in app.routes]
        assert "/" in routes
        assert "/health" in routes

    def test_app_middleware_configured(self):
        """Test that middleware is configured on the main app."""
        # Check that middleware is present
        middleware_types = [type(middleware) for middleware in app.user_middleware]
        
        # CORS middleware should be present
        from fastapi.middleware.cors import CORSMiddleware
        assert any(issubclass(mw_type, CORSMiddleware) for mw_type in middleware_types)

    def test_app_exception_handlers_configured(self):
        """Test that exception handlers are configured on the main app."""
        # Check that exception handlers are registered
        assert StarletteHTTPException in app.exception_handlers
        assert RequestValidationError in app.exception_handlers
```

```

