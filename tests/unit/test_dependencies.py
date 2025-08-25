"""
Unit tests for Dependencies module.

This module contains comprehensive unit tests for the dependency injection
functions used throughout the application.
"""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, validate_token
from app.domains.user.service import UserService
from models.user import User


class TestValidateToken:
    """Test cases for validate_token dependency."""

    @pytest.mark.asyncio
    async def test_validate_token_success(self):
        """Test successful token validation."""
        mock_token = MagicMock()
        mock_token.credentials = "valid_jwt_token"
        
        mock_payload = {
            "sub": "user_123",
            "email": "test@example.com",
            "username": "testuser"
        }
        
        with patch('app.core.dependencies.auth.verify_token') as mock_verify:
            mock_verify.return_value = mock_payload
            
            result = await validate_token(mock_token)
            
            assert result == mock_payload
            mock_verify.assert_called_once_with("valid_jwt_token")

    @pytest.mark.asyncio
    async def test_validate_token_none_token(self):
        """Test token validation with None token."""
        with pytest.raises(HTTPException) as exc_info:
            await validate_token(None)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Authentication token is required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_validate_token_empty_credentials(self):
        """Test token validation with empty credentials."""
        mock_token = MagicMock()
        mock_token.credentials = ""
        
        with pytest.raises(HTTPException) as exc_info:
            await validate_token(mock_token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Authentication token is required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_validate_token_none_credentials(self):
        """Test token validation with None credentials."""
        mock_token = MagicMock()
        mock_token.credentials = None
        
        with pytest.raises(HTTPException) as exc_info:
            await validate_token(mock_token)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Authentication token is required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_validate_token_verification_failure(self):
        """Test token validation when verification fails."""
        mock_token = MagicMock()
        mock_token.credentials = "invalid_token"
        
        with patch('app.core.dependencies.auth.verify_token') as mock_verify:
            mock_verify.return_value = None
            
            with pytest.raises(HTTPException) as exc_info:
                await validate_token(mock_token)
            
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Invalid authentication token" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_validate_token_verification_exception(self):
        """Test token validation when verification raises exception."""
        mock_token = MagicMock()
        mock_token.credentials = "problematic_token"
        
        with patch('app.core.dependencies.auth.verify_token') as mock_verify:
            mock_verify.side_effect = Exception("Verification error")
            
            with patch('app.core.dependencies.logger') as mock_logger:
                with pytest.raises(HTTPException) as exc_info:
                    await validate_token(mock_token)
                
                assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
                assert "Authentication failed" in exc_info.value.detail
                mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_token_http_exception_passthrough(self):
        """Test that HTTPException from auth is passed through."""
        mock_token = MagicMock()
        mock_token.credentials = "expired_token"
        
        original_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired"
        )
        
        with patch('app.core.dependencies.auth.verify_token') as mock_verify:
            mock_verify.side_effect = original_exception
            
            with pytest.raises(HTTPException) as exc_info:
                await validate_token(mock_token)
            
            # Should be the same exception
            assert exc_info.value is original_exception

    @pytest.mark.asyncio
    async def test_validate_token_www_authenticate_header(self):
        """Test that WWW-Authenticate header is set correctly."""
        mock_token = MagicMock()
        mock_token.credentials = None
        
        with pytest.raises(HTTPException) as exc_info:
            await validate_token(mock_token)
        
        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}


class TestGetCurrentUser:
    """Test cases for get_current_user dependency."""

    @pytest.mark.asyncio
    async def test_get_current_user_success(self, test_db):
        """Test successful user retrieval."""
        mock_request = MagicMock(spec=Request)
        mock_payload = {
            "sub": "clerk_user_123",
            "email": "test@example.com",
            "username": "testuser"
        }
        
        # Create a test user
        test_user = User(
            clerk_user_id="clerk_user_123",
            email="test@example.com",
            username="testuser",
            is_active=True
        )
        test_db.add(test_user)
        await test_db.commit()
        await test_db.refresh(test_user)
        
        result = await get_current_user(mock_request, mock_payload, test_db)
        
        assert result is not None
        assert result.clerk_user_id == "clerk_user_123"
        assert result.email == "test@example.com"
        assert result.username == "testuser"

    @pytest.mark.asyncio
    async def test_get_current_user_not_found(self, test_db):
        """Test user retrieval when user doesn't exist."""
        mock_request = MagicMock(spec=Request)
        mock_payload = {
            "sub": "nonexistent_user",
            "email": "notfound@example.com",
            "username": "notfound"
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request, mock_payload, test_db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "User not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_creates_new_user(self, test_db):
        """Test that new user is created when not found."""
        mock_request = MagicMock(spec=Request)
        mock_payload = {
            "sub": "new_clerk_user",
            "email": "newuser@example.com",
            "username": "newuser"
        }
        
        # Mock UserService to simulate user creation
        with patch('app.core.dependencies.UserService') as mock_user_service_class:
            mock_user_service = mock_user_service_class.return_value
            
            # First call returns None (user not found)
            # Second call returns the created user
            new_user = User(
                clerk_user_id="new_clerk_user",
                email="newuser@example.com",
                username="newuser",
                is_active=True
            )
            
            mock_user_service.get_or_create_user.return_value = None
            mock_user_service.get_or_create_user.return_value = new_user
            
            result = await get_current_user(mock_request, mock_payload, test_db)
            
            assert result == new_user
            mock_user_service.get_or_create_user.assert_called_once_with("new_clerk_user", mock_payload)

    @pytest.mark.asyncio
    async def test_get_current_user_inactive_user(self, test_db):
        """Test user retrieval with inactive user."""
        mock_request = MagicMock(spec=Request)
        mock_payload = {
            "sub": "inactive_user",
            "email": "inactive@example.com",
            "username": "inactive"
        }
        
        # Create an inactive test user
        test_user = User(
            clerk_user_id="inactive_user",
            email="inactive@example.com",
            username="inactive",
            is_active=False
        )
        test_db.add(test_user)
        await test_db.commit()
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request, mock_payload, test_db)
        
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "User account is inactive" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_missing_sub_in_payload(self, test_db):
        """Test user retrieval with missing 'sub' in payload."""
        mock_request = MagicMock(spec=Request)
        mock_payload = {
            "email": "test@example.com",
            "username": "testuser"
            # Missing 'sub' field
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request, mock_payload, test_db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid token payload - missing user ID" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_database_error(self, test_db):
        """Test user retrieval with database error."""
        mock_request = MagicMock(spec=Request)
        mock_payload = {
            "sub": "user_123",
            "email": "test@example.com",
            "username": "testuser"
        }
        
        with patch('app.core.dependencies.UserService') as mock_user_service_class:
            mock_user_service = mock_user_service_class.return_value
            mock_user_service.get_user_by_clerk_id.side_effect = Exception("Database error")
            
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_request, mock_payload, test_db)
            
            assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Authentication service error" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_user_service_integration(self, test_db):
        """Test integration with UserService."""
        mock_request = MagicMock(spec=Request)
        mock_payload = {
            "sub": "integration_user",
            "email": "integration@example.com",
            "username": "integration"
        }
        
        # Create a real UserService instance
        user_service = UserService(test_db)
        
        with patch('app.core.dependencies.UserService') as mock_user_service_class:
            mock_user_service_class.return_value = user_service
            
            # Create user first
            created_user = await user_service.create_user_from_clerk(mock_payload)
            
            # Now test retrieval
            result = await get_current_user(mock_request, mock_payload, test_db)
            
            assert result.clerk_user_id == created_user.clerk_user_id
            assert result.email == created_user.email
            assert result.username == created_user.username

    @pytest.mark.asyncio
    async def test_get_current_user_request_state_preservation(self, test_db):
        """Test that request state is preserved during user retrieval."""
        mock_request = MagicMock(spec=Request)
        mock_request.state.request_id = "req_123"
        mock_request.state.user_agent = "TestAgent/1.0"
        
        mock_payload = {
            "sub": "state_test_user",
            "email": "state@example.com",
            "username": "stateuser"
        }
        
        # Create user
        test_user = User(
            clerk_user_id="state_test_user",
            email="state@example.com",
            username="stateuser",
            is_active=True
        )
        test_db.add(test_user)
        await test_db.commit()
        
        result = await get_current_user(mock_request, mock_payload, test_db)
        
        # Request state should be preserved
        assert mock_request.state.request_id == "req_123"
        assert mock_request.state.user_agent == "TestAgent/1.0"
        assert result is not None


class TestDependencyIntegration:
    """Test integration between dependencies."""

    @pytest.mark.asyncio
    async def test_full_authentication_flow(self, test_db):
        """Test complete authentication flow from token to user."""
        # Mock JWT token
        mock_token = MagicMock()
        mock_token.credentials = "valid_jwt_token"
        
        mock_payload = {
            "sub": "flow_test_user",
            "email": "flow@example.com",
            "username": "flowuser"
        }
        
        # Create user for the flow
        test_user = User(
            clerk_user_id="flow_test_user",
            email="flow@example.com",
            username="flowuser",
            is_active=True
        )
        test_db.add(test_user)
        await test_db.commit()
        
        mock_request = MagicMock(spec=Request)
        
        with patch('app.core.dependencies.auth.verify_token') as mock_verify:
            mock_verify.return_value = mock_payload
            
            # Step 1: Validate token
            validated_payload = await validate_token(mock_token)
            assert validated_payload == mock_payload
            
            # Step 2: Get current user
            current_user = await get_current_user(mock_request, validated_payload, test_db)
            assert current_user.clerk_user_id == "flow_test_user"
            assert current_user.email == "flow@example.com"
            assert current_user.username == "flowuser"

    def test_security_bearer_configuration(self):
        """Test HTTPBearer security configuration."""
        from app.core.dependencies import security
        
        assert isinstance(security, HTTPBearer)
        # HTTPBearer should be configured properly for the dependency injection

```

```

