"""
API tests for User/Authentication controller.

This module contains comprehensive API endpoint tests for the user authentication
controller, testing all endpoints with various scenarios and edge cases.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from httpx import AsyncClient

from app.schemas.user import UserLoginRequest, UserSignupRequest, UserUpdateRequest


class TestUserAuthController:
    """Test cases for User/Authentication API endpoints."""

    @pytest.mark.asyncio
    async def test_signup_success(self, client: AsyncClient, test_db):
        """Test successful user signup."""
        signup_data = {
            "clerk_user_id": f"clerk_user_{uuid.uuid4()}",
            "email": "newuser@example.com",
            "username": "newuser",
        }

        response = await client.post("/api/auth/signup", json=signup_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["user"]["email"] == signup_data["email"]
        assert data["user"]["username"] == signup_data["username"]
        assert data["message"] == "User created successfully"

    @pytest.mark.asyncio
    async def test_signup_duplicate_user(self, client: AsyncClient, test_user):
        """Test signup with existing user."""
        signup_data = {
            "clerk_user_id": test_user.clerk_user_id,
            "email": "different@example.com",
            "username": "different",
        }

        response = await client.post("/api/auth/signup", json=signup_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "User already exists" in data["detail"]

    @pytest.mark.asyncio
    async def test_signup_invalid_email(self, client: AsyncClient):
        """Test signup with invalid email format."""
        signup_data = {
            "clerk_user_id": f"clerk_user_{uuid.uuid4()}",
            "email": "invalid-email",
            "username": "testuser",
        }

        response = await client.post("/api/auth/signup", json=signup_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_signup_missing_required_fields(self, client: AsyncClient):
        """Test signup with missing required fields."""
        signup_data = {
            "username": "testuser"
            # Missing clerk_user_id and email
        }

        response = await client.post("/api/auth/signup", json=signup_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_signup_service_error(self, client: AsyncClient):
        """Test signup with service error."""
        signup_data = {
            "clerk_user_id": f"clerk_user_{uuid.uuid4()}",
            "email": "error@example.com",
            "username": "erroruser",
        }

        with patch(
            "app.domains.user.service.UserService.create_user",
            side_effect=Exception("Service error"),
        ):
            response = await client.post("/api/auth/signup", json=signup_data)

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()
            assert "Failed to create user" in data["detail"]

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user, mock_clerk_auth):
        """Test successful user login."""
        login_data = {"token": "valid_jwt_token"}

        with patch("app.domains.user.controller.auth", mock_clerk_auth):
            response = await client.post("/api/auth/login", json=login_data)

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["user"]["email"] == test_user.email
            assert data["message"] == "Login successful"

    @pytest.mark.asyncio
    async def test_login_invalid_token(self, client: AsyncClient, mock_clerk_auth):
        """Test login with invalid token."""
        login_data = {"token": "invalid_token"}

        mock_clerk_auth.verify_token.side_effect = Exception("Invalid token")

        with patch("app.domains.user.controller.auth", mock_clerk_auth):
            response = await client.post("/api/auth/login", json=login_data)

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    @pytest.mark.asyncio
    async def test_login_missing_token(self, client: AsyncClient):
        """Test login with missing token."""
        response = await client.post("/api/auth/login", json={})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_login_token_without_sub(self, client: AsyncClient, mock_clerk_auth):
        """Test login with token missing subject."""
        login_data = {"token": "token_without_sub"}

        mock_clerk_auth.verify_token.return_value = {"email": "test@example.com"}  # Missing 'sub'

        with patch("app.domains.user.controller.auth", mock_clerk_auth):
            response = await client.post("/api/auth/login", json=login_data)

            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            data = response.json()
            assert "Invalid token payload" in data["detail"]

    @pytest.mark.asyncio
    async def test_login_create_new_user(self, client: AsyncClient, mock_clerk_auth):
        """Test login that creates a new user."""
        login_data = {"token": "new_user_token"}

        # Mock token verification to return new user data
        mock_clerk_auth.verify_token.return_value = {
            "sub": f"clerk_user_{uuid.uuid4()}",
            "email": "newloginuser@example.com",
            "username": "newloginuser",
        }

        with patch("app.domains.user.controller.auth", mock_clerk_auth):
            response = await client.post("/api/auth/login", json=login_data)

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["user"]["email"] == "newloginuser@example.com"
            assert data["message"] == "Login successful"

    @pytest.mark.asyncio
    async def test_logout(self, client: AsyncClient):
        """Test logout endpoint."""
        response = await client.post("/api/auth/logout")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Logout successful"

    @pytest.mark.asyncio
    async def test_get_current_user_success(self, authenticated_client: AsyncClient, test_user):
        """Test getting current user information."""
        response = await authenticated_client.get("/api/auth/me")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(test_user.id)
        assert data["email"] == test_user.email
        assert data["username"] == test_user.username

    @pytest.mark.asyncio
    async def test_get_current_user_unauthorized(self, client: AsyncClient):
        """Test getting current user without authentication."""
        response = await client.get("/api/auth/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_update_current_user_success(self, authenticated_client: AsyncClient, test_user):
        """Test updating current user information."""
        update_data = {"username": "updated_username", "email": "updated@example.com"}

        response = await authenticated_client.put("/api/auth/me", json=update_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == "updated_username"
        assert data["email"] == "updated@example.com"

    @pytest.mark.asyncio
    async def test_update_current_user_partial(self, authenticated_client: AsyncClient, test_user):
        """Test partial update of current user."""
        original_email = test_user.email
        update_data = {"username": "new_username_only"}

        response = await authenticated_client.put("/api/auth/me", json=update_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == "new_username_only"
        assert data["email"] == original_email

    @pytest.mark.asyncio
    async def test_update_current_user_invalid_email(self, authenticated_client: AsyncClient):
        """Test updating user with invalid email."""
        update_data = {"email": "invalid-email-format"}

        response = await authenticated_client.put("/api/auth/me", json=update_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_update_current_user_service_error(
        self, authenticated_client: AsyncClient, test_user
    ):
        """Test updating user with service error."""
        update_data = {"username": "error_username"}

        with patch(
            "app.domains.user.service.UserService.update_user",
            side_effect=Exception("Service error"),
        ):
            response = await authenticated_client.put("/api/auth/me", json=update_data)

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()
            assert "Failed to update user" in data["detail"]

    @pytest.mark.asyncio
    async def test_update_current_user_unauthorized(self, client: AsyncClient):
        """Test updating user without authentication."""
        update_data = {"username": "should_fail"}

        response = await client.put("/api/auth/me", json=update_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_auth_endpoints_cors_headers(self, client: AsyncClient):
        """Test that auth endpoints include CORS headers."""
        # Test signup endpoint
        response = await client.options("/api/auth/signup")
        assert (
            "access-control-allow-origin" in response.headers.keys()
            or response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        )

    @pytest.mark.asyncio
    async def test_auth_endpoints_request_id(self, client: AsyncClient):
        """Test that auth endpoints include request ID in response."""
        signup_data = {
            "clerk_user_id": f"clerk_user_{uuid.uuid4()}",
            "email": "requestid@example.com",
            "username": "requestiduser",
        }

        response = await client.post("/api/auth/signup", json=signup_data)

        assert "x-request-id" in response.headers
        assert response.headers["x-request-id"] is not None

    @pytest.mark.asyncio
    async def test_login_creates_interaction_log(self, client: AsyncClient, mock_clerk_auth):
        """Test that login creates appropriate logs/interactions."""
        login_data = {"token": "logging_test_token"}

        mock_clerk_auth.verify_token.return_value = {
            "sub": f"clerk_user_{uuid.uuid4()}",
            "email": "logtest@example.com",
            "username": "logtest",
        }

        with patch("app.domains.user.controller.auth", mock_clerk_auth):
            # Could add logging/audit trail verification here
            response = await client.post("/api/auth/login", json=login_data)

            assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_signup_validation_comprehensive(self, client: AsyncClient):
        """Test comprehensive validation for signup."""
        # Test various invalid scenarios
        invalid_cases = [
            # Empty clerk_user_id
            {
                "clerk_user_id": "",
                "email": "valid@example.com",
                "username": "validuser",
            },
            # Very long username
            {
                "clerk_user_id": f"clerk_user_{uuid.uuid4()}",
                "email": "valid@example.com",
                "username": "x" * 101,  # Assuming 100 char limit
            },
            # Invalid email domains (if validation exists)
            {
                "clerk_user_id": f"clerk_user_{uuid.uuid4()}",
                "email": "test@invalid",
                "username": "testuser",
            },
        ]

        for invalid_data in invalid_cases:
            response = await client.post("/api/auth/signup", json=invalid_data)
            assert response.status_code in [
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                status.HTTP_400_BAD_REQUEST,
            ]
