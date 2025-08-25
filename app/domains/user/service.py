# app/domains/user/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from typing import Optional, Dict, Any
from uuid import UUID
from models import User


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_clerk_id(self, clerk_user_id: str) -> Optional[User]:
        """Get a user by Clerk user ID."""
        result = await self.db.execute(select(User).where(User.clerk_user_id == clerk_user_id))
        return result.scalar_one_or_none()

    async def create_user(self, clerk_user_id: str, email: str, username: str = None) -> User:
        """Create a new user."""
        user = User(clerk_user_id=clerk_user_id, email=email, username=username)

        try:
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
            return user
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise e

    async def get_or_create_user(self, clerk_user_id: str, clerk_payload: dict) -> User:
        """Get existing user or create new one from Clerk payload."""
        user = await self.get_user_by_clerk_id(clerk_user_id)
        if not user:
            user = await self.create_user(
                clerk_user_id=clerk_user_id,
                email=clerk_payload.get("email"),
                username=clerk_payload.get("username"),
            )
        return user

    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Get a user by ID."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def update_user(
        self, user_id: UUID, username: str = None, email: str = None
    ) -> Optional[User]:
        """Update user information."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return None

        try:
            if username is not None:
                user.username = username
            if email is not None:
                user.email = email

            await self.db.commit()
            await self.db.refresh(user)
            return user
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise e

    async def deactivate_user(self, user_id: UUID) -> Optional[User]:
        """Deactivate a user account."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return None

        try:
            user.is_active = False
            await self.db.commit()
            await self.db.refresh(user)
            return user
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise e

    async def activate_user(self, user_id: UUID) -> Optional[User]:
        """Activate a user account."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return None

        try:
            user.is_active = True
            await self.db.commit()
            await self.db.refresh(user)
            return user
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise e

    async def delete_user(self, user_id: UUID) -> bool:
        """Delete a user and all associated data."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False

        try:
            await self.db.delete(user)
            await self.db.commit()
            return True
        except SQLAlchemyError as e:
            await self.db.rollback()
            raise e

    async def get_user_profile(self, user_id: UUID) -> Optional[Dict[str, Any]]:
        """Get complete user profile information."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return None

        return {
            "id": user.id,
            "clerk_user_id": user.clerk_user_id,
            "email": user.email,
            "username": user.username,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }
