# app/core/dependencies.py
import logging

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import ClerkAuthenticator
from app.database import get_db
from app.domains.user.service import UserService
from models import User

logger = logging.getLogger(__name__)

security = HTTPBearer()
auth = ClerkAuthenticator()


async def validate_token(token: str = Depends(security)) -> dict:
    """Validate and decode JWT token from Clerk.

    Returns:
        dict: Decoded token payload

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        if not token or not token.credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication token is required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Verify token with Clerk
        payload = await auth.verify_token(token.credentials)

        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return payload

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Token validation error: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_current_user(
    request: Request,
    payload: dict = Depends(validate_token),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current authenticated user from JWT payload.

    Returns:
        User: Current authenticated user

    Raises:
        HTTPException: If user not found or inactive
    """
    try:
        clerk_user_id = payload.get("sub")

        if not clerk_user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload - missing user ID",
            )

        # Get or create user in local database
        user_service = UserService(db)
        user = await user_service.get_or_create_user(clerk_user_id, payload)

        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive"
            )

        # Add user info to request state for logging
        request.state.user_id = user.id
        request.state.clerk_user_id = clerk_user_id

        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error("User authentication error: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error",
        ) from e


async def get_optional_user(
    payload: dict | None = Depends(validate_token),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Get current user if authenticated, otherwise return None.

    Used for optional authentication endpoints.

    Returns:
        Optional[User]: Current user if authenticated, None otherwise
    """
    if not payload:
        return None

    try:
        clerk_user_id = payload.get("sub")
        if not clerk_user_id:
            return None

        user_service = UserService(db)
        user = await user_service.get_or_create_user(clerk_user_id, payload)
        return user if user and user.is_active else None

    except Exception as e:
        logger.warning("Optional user authentication failed: %s", str(e))
        return None
