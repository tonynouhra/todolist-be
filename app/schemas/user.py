"""User-related Pydantic schemas for request/response validation."""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from .base import BaseModelSchema, BaseSchema


class UserSignupRequest(BaseSchema):
    """Schema for user signup request."""
    email: EmailStr = Field(..., description="User's email address")
    username: Optional[str] = Field(None, max_length=100, description="Optional username")
    clerk_user_id: str = Field(..., max_length=255, description="Clerk user ID")


class UserLoginRequest(BaseSchema):
    """Schema for user login request."""
    token: str = Field(..., description="Clerk JWT token")


class UserResponse(BaseModelSchema):
    """Schema for user response data."""
    clerk_user_id: str
    email: str
    username: Optional[str]
    is_active: bool


class AuthResponse(BaseSchema):
    """Schema for authentication response."""
    user: UserResponse
    message: str = "Authentication successful"


class LogoutResponse(BaseSchema):
    """Schema for logout response."""
    message: str = "Logout successful"


class UserUpdateRequest(BaseSchema):
    """Schema for updating user information."""
    username: Optional[str] = Field(None, max_length=100, description="Username to update")
    email: Optional[EmailStr] = Field(None, description="Email to update")