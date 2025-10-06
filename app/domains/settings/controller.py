"""Settings controller endpoints for managing user preferences."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.database import get_db
from app.domains.settings.service import SettingsService
from app.schemas.settings import UserSettingsResponse, UserSettingsUpdate
from models.user import User


router = APIRouter(prefix="/api/settings", tags=["Settings"])


@router.get("", response_model=UserSettingsResponse)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's settings.

    This endpoint retrieves the authenticated user's settings,
    creating default settings if they don't exist yet.
    """
    settings_service = SettingsService(db)

    try:
        settings = await settings_service.get_user_settings(current_user.id)
        return UserSettingsResponse.model_validate(settings)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve settings: {str(e)}",
        ) from e


@router.put("", response_model=UserSettingsResponse)
async def update_settings(
    update_data: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user's settings.

    This endpoint allows users to update their preferences.
    Only provided fields will be updated; others remain unchanged.
    """
    settings_service = SettingsService(db)

    try:
        updated_settings = await settings_service.update_user_settings(
            user_id=current_user.id,
            theme=update_data.theme,
            language=update_data.language,
            timezone=update_data.timezone,
            notifications_enabled=update_data.notifications_enabled,
            email_notifications=update_data.email_notifications,
            push_notifications=update_data.push_notifications,
        )

        return UserSettingsResponse.model_validate(updated_settings)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update settings: {str(e)}",
        ) from e


@router.post("/reset", response_model=UserSettingsResponse)
async def reset_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reset current user's settings to defaults.

    This endpoint resets all user settings to their default values:
    - theme: system
    - language: en
    - timezone: UTC
    - All notifications: enabled
    """
    settings_service = SettingsService(db)

    try:
        reset_settings = await settings_service.reset_user_settings(current_user.id)
        return UserSettingsResponse.model_validate(reset_settings)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset settings: {str(e)}",
        ) from e
