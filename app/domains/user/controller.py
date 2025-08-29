"""User authentication controller endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.security import ClerkAuthenticator
from app.database import get_db
from app.domains.user.service import UserService
from app.schemas.user import (
    AuthResponse,
    LogoutResponse,
    UserLoginRequest,
    UserResponse,
    UserSignupRequest,
    UserUpdateRequest,
)
from models.user import User

router = APIRouter(prefix="/api/auth", tags=["Authentication"])
auth = ClerkAuthenticator()


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(signup_data: UserSignupRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user with Clerk authentication.

    This endpoint creates a new user account in the local database using
    the provided Clerk user ID and user information.
    """
    user_service = UserService(db)

    # Check if user already exists
    existing_user = await user_service.get_user_by_clerk_id(signup_data.clerk_user_id)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists")

    # Create new user
    try:
        user = await user_service.create_user(
            clerk_user_id=signup_data.clerk_user_id,
            email=str(signup_data.email),
            username=signup_data.username,
        )

        return AuthResponse(
            user=UserResponse.model_validate(user), message="User created successfully"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}",
        )


@router.post("/login", response_model=AuthResponse)
async def login(login_data: UserLoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate user with Clerk JWT token.

    This endpoint verifies the provided JWT token with Clerk and returns
    user information if authentication is successful.
    """
    try:
        # Verify token with Clerk
        payload = await auth.verify_token(login_data.token)
        clerk_user_id = payload.get("sub")

        if not clerk_user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
            )

        # Get or create user in local database
        user_service = UserService(db)
        user = await user_service.get_or_create_user(clerk_user_id, payload)

        return AuthResponse(user=UserResponse.model_validate(user), message="Login successful")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication failed: {str(e)}",
        )


@router.post("/logout", response_model=LogoutResponse)
async def logout():
    """Logout endpoint.

    Since we're using Clerk for authentication, the actual logout logic
    is handled on the client side. This endpoint just provides a
    standardized logout response.
    """
    return LogoutResponse(message="Logout successful")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user information.

    This endpoint returns the profile information of the currently
    authenticated user.
    """
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    update_data: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current authenticated user information.

    This endpoint allows users to update their profile information
    such as username and email.
    """
    user_service = UserService(db)

    try:
        updated_user = await user_service.update_user(
            user_id=current_user.id,
            username=update_data.username,
            email=update_data.email,
        )

        return UserResponse.model_validate(updated_user)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {str(e)}",
        )
