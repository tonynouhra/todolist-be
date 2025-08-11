# app/core/dependencies.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.core.security import ClerkAuthenticator
from app.domains.user.service import UserService
from models import User

security = HTTPBearer()
auth = ClerkAuthenticator()

async def get_current_user(
    token: str = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    # Verify token with Clerk
    payload = await auth.verify_token(token.credentials)
    clerk_user_id = payload.get("sub")
    
    if not clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    # Get or create user in local database
    user_service = UserService(db)
    user = await user_service.get_or_create_user(clerk_user_id, payload)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user