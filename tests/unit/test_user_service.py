# ruff: noqa: SIM117
"""
Unit tests for UserService.

This module contains comprehensive unit tests for the UserService class,
testing all business logic methods with various scenarios and edge cases.
"""

import uuid
from unittest.mock import patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.domains.user.service import UserService


class TestUserService:
    """Test cases for UserService."""

    @pytest.mark.asyncio
    async def test_get_user_by_clerk_id_existing_user(self, test_db, test_user):
        """Test getting an existing user by clerk_user_id."""
        service = UserService(test_db)

        result = await service.get_user_by_clerk_id(test_user.clerk_user_id)

        assert result is not None
        assert result.id == test_user.id
        assert result.email == test_user.email
        assert result.clerk_user_id == test_user.clerk_user_id

    @pytest.mark.asyncio
    async def test_get_user_by_clerk_id_nonexistent_user(self, test_db):
        """Test getting a non-existent user by clerk_user_id."""
        service = UserService(test_db)

        result = await service.get_user_by_clerk_id("nonexistent_clerk_id")

        assert result is None

    @pytest.mark.asyncio
    async def test_create_user_success(self, test_db):
        """Test successful user creation."""
        service = UserService(test_db)
        clerk_user_id = f"clerk_user_{uuid.uuid4()}"
        email = "newuser@example.com"
        username = "newuser"

        result = await service.create_user(
            clerk_user_id=clerk_user_id, email=email, username=username
        )

        assert result is not None
        assert result.clerk_user_id == clerk_user_id
        assert result.email == email
        assert result.username == username
        assert result.is_active is True
        assert result.id is not None

    @pytest.mark.asyncio
    async def test_create_user_without_username(self, test_db):
        """Test user creation without username."""
        service = UserService(test_db)
        clerk_user_id = f"clerk_user_{uuid.uuid4()}"
        email = "nousername@example.com"

        result = await service.create_user(clerk_user_id=clerk_user_id, email=email)

        assert result is not None
        assert result.clerk_user_id == clerk_user_id
        assert result.email == email
        assert result.username is None
        assert result.is_active is True

    @pytest.mark.asyncio
    async def test_create_user_database_error(self, test_db):
        """Test user creation with database error."""
        service = UserService(test_db)

        # Mock database error
        with patch.object(test_db, "commit", side_effect=SQLAlchemyError("Database error")):
            with patch.object(test_db, "rollback") as mock_rollback:
                with pytest.raises(SQLAlchemyError):
                    await service.create_user(
                        clerk_user_id="test_clerk_id", email="error@example.com"
                    )
                mock_rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_or_create_user_existing_user(self, test_db, test_user):
        """Test get_or_create_user with existing user."""
        service = UserService(test_db)
        clerk_payload = {
            "email": "different@example.com",
            "username": "different_username",
        }

        result = await service.get_or_create_user(test_user.clerk_user_id, clerk_payload)

        # Should return existing user, not create new one
        assert result.id == test_user.id
        assert result.email == test_user.email  # Original email preserved
        assert result.username == test_user.username  # Original username preserved

    @pytest.mark.asyncio
    async def test_get_or_create_user_new_user(self, test_db):
        """Test get_or_create_user with new user."""
        service = UserService(test_db)
        clerk_user_id = f"clerk_user_{uuid.uuid4()}"
        clerk_payload = {"email": "newuser@example.com", "username": "newusername"}

        result = await service.get_or_create_user(clerk_user_id, clerk_payload)

        assert result is not None
        assert result.clerk_user_id == clerk_user_id
        assert result.email == clerk_payload["email"]
        assert result.username == clerk_payload["username"]
        assert result.is_active is True

    @pytest.mark.asyncio
    async def test_get_or_create_user_incomplete_payload(self, test_db):
        """Test get_or_create_user with incomplete clerk payload."""
        service = UserService(test_db)
        clerk_user_id = f"clerk_user_{uuid.uuid4()}"
        clerk_payload = {
            "email": "incomplete@example.com"
            # Missing username
        }

        result = await service.get_or_create_user(clerk_user_id, clerk_payload)

        assert result is not None
        assert result.clerk_user_id == clerk_user_id
        assert result.email == clerk_payload["email"]
        assert result.username is None

    @pytest.mark.asyncio
    async def test_update_user_success(self, test_db, test_user):
        """Test successful user update."""
        service = UserService(test_db)
        new_username = "updated_username"
        new_email = "updated@example.com"

        result = await service.update_user(
            user_id=test_user.id, username=new_username, email=new_email
        )

        assert result is not None
        assert result.id == test_user.id
        assert result.username == new_username
        assert result.email == new_email

    @pytest.mark.asyncio
    async def test_update_user_partial_update(self, test_db, test_user):
        """Test partial user update."""
        service = UserService(test_db)
        original_email = test_user.email
        new_username = "partial_update_username"

        result = await service.update_user(user_id=test_user.id, username=new_username)

        assert result is not None
        assert result.id == test_user.id
        assert result.username == new_username
        assert result.email == original_email  # Should remain unchanged

    @pytest.mark.asyncio
    async def test_update_user_nonexistent_user(self, test_db):
        """Test updating a non-existent user."""
        service = UserService(test_db)
        fake_user_id = uuid.uuid4()

        result = await service.update_user(user_id=fake_user_id, username="new_username")

        assert result is None

    @pytest.mark.asyncio
    async def test_update_user_database_error(self, test_db, test_user):
        """Test user update with database error."""
        service = UserService(test_db)

        with patch.object(test_db, "commit", side_effect=SQLAlchemyError("Database error")):
            with patch.object(test_db, "rollback") as mock_rollback:
                with pytest.raises(SQLAlchemyError):
                    await service.update_user(user_id=test_user.id, username="error_username")
                mock_rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_user_by_id_success(self, test_db, test_user):
        """Test getting user by ID successfully."""
        service = UserService(test_db)

        result = await service.get_user_by_id(test_user.id)

        assert result is not None
        assert result.id == test_user.id
        assert result.email == test_user.email

    @pytest.mark.asyncio
    async def test_get_user_by_id_nonexistent(self, test_db):
        """Test getting non-existent user by ID."""
        service = UserService(test_db)
        fake_id = uuid.uuid4()

        result = await service.get_user_by_id(fake_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_deactivate_user_success(self, test_db, test_user):
        """Test user deactivation."""
        service = UserService(test_db)
        assert test_user.is_active is True

        result = await service.deactivate_user(test_user.id)

        assert result is not None
        assert result.id == test_user.id
        assert result.is_active is False

    @pytest.mark.asyncio
    async def test_deactivate_user_nonexistent(self, test_db):
        """Test deactivating non-existent user."""
        service = UserService(test_db)
        fake_id = uuid.uuid4()

        result = await service.deactivate_user(fake_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_activate_user_success(self, test_db, test_user):
        """Test user activation."""
        service = UserService(test_db)

        # First deactivate
        test_user.is_active = False
        await test_db.commit()

        result = await service.activate_user(test_user.id)

        assert result is not None
        assert result.id == test_user.id
        assert result.is_active is True

    @pytest.mark.asyncio
    async def test_delete_user_success(self, test_db, test_user):
        """Test successful user deletion."""
        service = UserService(test_db)
        user_id = test_user.id

        success = await service.delete_user(user_id)

        assert success is True

        # Verify user is deleted
        deleted_user = await service.get_user_by_id(user_id)
        assert deleted_user is None

    @pytest.mark.asyncio
    async def test_delete_user_nonexistent(self, test_db):
        """Test deleting non-existent user."""
        service = UserService(test_db)
        fake_id = uuid.uuid4()

        success = await service.delete_user(fake_id)

        assert success is False

    @pytest.mark.asyncio
    async def test_delete_user_with_cascade(self, test_db, test_user, test_todo, test_project):
        """Test user deletion cascades to related objects."""
        service = UserService(test_db)
        user_id = test_user.id

        # Verify related objects exist
        assert test_todo.user_id == user_id
        assert test_project.user_id == user_id

        success = await service.delete_user(user_id)

        assert success is True

        # Verify user and related objects are deleted
        deleted_user = await service.get_user_by_id(user_id)
        assert deleted_user is None

    @pytest.mark.asyncio
    async def test_get_user_profile_success(self, test_db, test_user):
        """Test getting complete user profile."""
        service = UserService(test_db)

        profile = await service.get_user_profile(test_user.id)

        assert profile is not None
        assert profile["id"] == test_user.id
        assert profile["email"] == test_user.email
        assert profile["username"] == test_user.username
        assert profile["is_active"] == test_user.is_active
        assert "created_at" in profile
        assert "updated_at" in profile

    @pytest.mark.asyncio
    async def test_get_user_profile_nonexistent(self, test_db):
        """Test getting profile for non-existent user."""
        service = UserService(test_db)
        fake_id = uuid.uuid4()

        profile = await service.get_user_profile(fake_id)

        assert profile is None
