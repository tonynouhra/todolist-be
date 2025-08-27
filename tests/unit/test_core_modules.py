"""
Unit tests for Core modules - Simple tests to boost coverage.

This module contains basic tests for core functionality to reach 80% coverage.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException, Request, status

from app.core.dependencies import get_current_user, validate_token
from app.core.security import ClerkAuthenticator
from models.user import User


class TestCoreDependencies:
    """Test core dependency functions."""

    @pytest.mark.asyncio
    async def test_validate_token_success(self):
        """Test successful token validation."""
        mock_token = MagicMock()
        mock_token.credentials = "valid_jwt_token"

        mock_payload = {
            "sub": "user_123",
            "email": "test@example.com",
            "username": "testuser",
        }

        with patch("app.core.dependencies.auth.verify_token") as mock_verify:
            mock_verify.return_value = mock_payload

            result = await validate_token(mock_token)

            assert result == mock_payload
            mock_verify.assert_called_once_with("valid_jwt_token")

    @pytest.mark.asyncio
    async def test_validate_token_no_credentials(self):
        """Test token validation with missing credentials."""
        mock_token = MagicMock()
        mock_token.credentials = None

        with pytest.raises(HTTPException) as exc_info:
            await validate_token(mock_token)

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

    @pytest.mark.asyncio
    async def test_validate_token_invalid_payload(self):
        """Test token validation with invalid payload."""
        mock_token = MagicMock()
        mock_token.credentials = "invalid_token"

        with patch("app.core.dependencies.auth.verify_token") as mock_verify:
            mock_verify.return_value = None

            with pytest.raises(HTTPException) as exc_info:
                await validate_token(mock_token)

            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Invalid authentication token" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_validate_token_exception_handling(self):
        """Test token validation exception handling."""
        mock_token = MagicMock()
        mock_token.credentials = "problematic_token"

        with patch("app.core.dependencies.auth.verify_token") as mock_verify:
            mock_verify.side_effect = Exception("Verification error")

            with patch("app.core.dependencies.logger") as mock_logger:
                with pytest.raises(HTTPException) as exc_info:
                    await validate_token(mock_token)

                assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
                assert "Authentication failed" in exc_info.value.detail
                mock_logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_current_user_success(self, test_db):
        """Test successful user retrieval."""
        mock_request = MagicMock(spec=Request)
        mock_request.state = MagicMock()

        mock_payload = {
            "sub": "clerk_user_123",
            "email": "test@example.com",
            "username": "testuser",
        }

        test_user = User(
            clerk_user_id="clerk_user_123",
            email="test@example.com",
            username="testuser",
            is_active=True,
        )

        with patch("app.core.dependencies.UserService") as mock_user_service_class:
            mock_user_service = mock_user_service_class.return_value
            mock_user_service.get_or_create_user = AsyncMock(return_value=test_user)

            result = await get_current_user(mock_request, mock_payload, test_db)

            assert result == test_user
            # Verify request state is set
            assert mock_request.state.clerk_user_id == "clerk_user_123"

    @pytest.mark.asyncio
    async def test_get_current_user_no_sub(self, test_db):
        """Test user retrieval with missing sub."""
        mock_request = MagicMock(spec=Request)
        mock_request.state = MagicMock()

        mock_payload = {
            "email": "test@example.com",
            "username": "testuser",
            # Missing 'sub' field
        }

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_request, mock_payload, test_db)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid token payload - missing user ID" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_no_user_found(self, test_db):
        """Test user retrieval when user not found."""
        mock_request = MagicMock(spec=Request)
        mock_request.state = MagicMock()

        mock_payload = {"sub": "nonexistent_user", "email": "notfound@example.com"}

        with patch("app.core.dependencies.UserService") as mock_user_service_class:
            mock_user_service = mock_user_service_class.return_value
            mock_user_service.get_or_create_user = AsyncMock(return_value=None)

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_request, mock_payload, test_db)

            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_get_current_user_inactive_user(self, test_db):
        """Test user retrieval with inactive user."""
        mock_request = MagicMock(spec=Request)
        mock_request.state = MagicMock()

        mock_payload = {"sub": "inactive_user", "email": "inactive@example.com"}

        inactive_user = User(
            clerk_user_id="inactive_user",
            email="inactive@example.com",
            username="inactive",
            is_active=False,
        )

        with patch("app.core.dependencies.UserService") as mock_user_service_class:
            mock_user_service = mock_user_service_class.return_value
            mock_user_service.get_or_create_user = AsyncMock(return_value=inactive_user)

            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_request, mock_payload, test_db)

            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
            assert "User account is inactive" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_service_error(self, test_db):
        """Test user retrieval with service error."""
        mock_request = MagicMock(spec=Request)
        mock_request.state = MagicMock()

        mock_payload = {"sub": "user_123", "email": "test@example.com"}

        with patch("app.core.dependencies.UserService") as mock_user_service_class:
            mock_user_service = mock_user_service_class.return_value
            mock_user_service.get_or_create_user.side_effect = Exception("Database error")

            with patch("app.core.dependencies.logger") as mock_logger:
                with pytest.raises(HTTPException) as exc_info:
                    await get_current_user(mock_request, mock_payload, test_db)

                assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
                assert "Authentication service error" in exc_info.value.detail
                mock_logger.error.assert_called_once()


class TestClerkAuthenticator:
    """Test ClerkAuthenticator class."""

    def test_authenticator_initialization(self):
        """Test ClerkAuthenticator initialization."""
        with patch("app.core.security.settings") as mock_settings:
            mock_settings.clerk_api_url = "https://api.clerk.com"
            mock_settings.clerk_secret_key = "test_secret"

            auth = ClerkAuthenticator()

            assert auth.clerk_api_url == "https://api.clerk.com"
            assert auth.secret_key == "test_secret"

    @pytest.mark.asyncio
    async def test_verify_token_success(self):
        """Test successful token verification."""
        test_token = jwt.encode(
            {
                "sub": "user_123",
                "email": "test@example.com",
                "username": "testuser",
                "exp": 9999999999,  # Far future expiration
            },
            "secret",
            algorithm="HS256",
        )

        auth = ClerkAuthenticator()
        result = await auth.verify_token(test_token)

        assert result["sub"] == "user_123"
        assert result["email"] == "test@example.com"
        assert result["username"] == "testuser"

    @pytest.mark.asyncio
    async def test_verify_token_invalid_format(self):
        """Test token verification with invalid token format."""
        auth = ClerkAuthenticator()

        with pytest.raises(HTTPException) as exc_info:
            await auth.verify_token("invalid_token")

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid authentication token" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_verify_token_empty(self):
        """Test token verification with empty token."""
        auth = ClerkAuthenticator()

        with pytest.raises(HTTPException) as exc_info:
            await auth.verify_token("")

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_verify_token_jwt_decode_error(self):
        """Test token verification with JWT decode error."""
        with patch("app.core.security.jwt.decode") as mock_decode:
            mock_decode.side_effect = Exception("Invalid token")

            auth = ClerkAuthenticator()

            with pytest.raises(HTTPException) as exc_info:
                await auth.verify_token("some.token.here")

            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_jwks_success(self):
        """Test JWKS retrieval."""
        mock_jwks = {"keys": [{"kty": "RSA", "kid": "test"}]}

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = mock_jwks
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

            auth = ClerkAuthenticator()
            result = await auth.get_jwks()

            assert result == mock_jwks

    @pytest.mark.asyncio
    async def test_get_optional_user_success(self, test_db):
        """Test optional user function."""
        from app.core.dependencies import get_optional_user

        mock_payload = {"sub": "user_123", "email": "test@example.com"}

        test_user = User(
            clerk_user_id="user_123",
            email="test@example.com",
            username="testuser",
            is_active=True,
        )

        with patch("app.core.dependencies.UserService") as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_or_create_user = AsyncMock(return_value=test_user)

            result = await get_optional_user(mock_payload, test_db)
            assert result == test_user

    @pytest.mark.asyncio
    async def test_get_optional_user_none_payload(self, test_db):
        """Test optional user with no payload."""
        from app.core.dependencies import get_optional_user

        result = await get_optional_user(None, test_db)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_optional_user_no_sub(self, test_db):
        """Test optional user with no sub."""
        from app.core.dependencies import get_optional_user

        mock_payload = {"email": "test@example.com"}  # No sub

        result = await get_optional_user(mock_payload, test_db)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_optional_user_inactive(self, test_db):
        """Test optional user with inactive user."""
        from app.core.dependencies import get_optional_user

        mock_payload = {"sub": "user_123"}

        inactive_user = User(clerk_user_id="user_123", email="test@example.com", is_active=False)

        with patch("app.core.dependencies.UserService") as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_or_create_user = AsyncMock(return_value=inactive_user)

            result = await get_optional_user(mock_payload, test_db)
            assert result is None

    @pytest.mark.asyncio
    async def test_get_optional_user_exception(self, test_db):
        """Test optional user with exception."""
        from app.core.dependencies import get_optional_user

        mock_payload = {"sub": "user_123"}

        with patch("app.core.dependencies.UserService") as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service.get_or_create_user.side_effect = Exception("Database error")

            with patch("app.core.dependencies.logger") as mock_logger:
                result = await get_optional_user(mock_payload, test_db)
                assert result is None
                mock_logger.warning.assert_called_once()


class TestDatabaseModule:
    """Test database module functions."""

    @pytest.mark.asyncio
    async def test_get_db_function(self):
        """Test get_db function."""
        from app.database import get_db

        # Test that get_db returns an async session generator
        db_gen = get_db()
        db_session = await db_gen.__anext__()

        # Should be an AsyncSession
        assert db_session is not None

        # Clean up
        await db_session.close()

        try:
            await db_gen.__anext__()
        except StopAsyncIteration:
            pass  # Expected

    def test_database_base_import(self):
        """Test Base import from database module."""
        from app.database import Base

        # Should be able to import Base
        assert Base is not None
        assert hasattr(Base, "metadata")
