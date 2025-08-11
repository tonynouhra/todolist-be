# app/domains/user/service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from typing import Optional


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_by_clerk_id(self, clerk_user_id: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.clerk_user_id == clerk_user_id)
        )
        return result.scalar_one_or_none()

    async def create_user(self, clerk_user_id: str, email: str, username: str = None) -> User:
        user = User(
            clerk_user_id=clerk_user_id,
            email=email,
            username=username
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def get_or_create_user(self, clerk_user_id: str, clerk_payload: dict) -> User:
        user = await self.get_user_by_clerk_id(clerk_user_id)
        if not user:
            user = await self.create_user(
                clerk_user_id=clerk_user_id,
                email=clerk_payload.get("email"),
                username=clerk_payload.get("username")
            )
        return user