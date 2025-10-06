"""Chat API controller with FastAPI endpoints."""

import logging
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Path, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, validate_token
from app.domains.chat.service import ChatService
from app.exceptions.ai import AIServiceError
from app.schemas.base import ResponseSchema
from app.schemas.chat import ChatRequest
from models.user import User


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/chat",
    tags=["chat"],
    dependencies=[Depends(validate_token)],
)


@router.post("/message", response_model=ResponseSchema, status_code=201)
async def send_chat_message(
    _request: Request,
    chat_request: ChatRequest = Body(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a message to the AI chat assistant.

    Args:
        chat_request: Chat request with message and optional conversation ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Chat response with AI reply and any actions taken
    """
    try:
        service = ChatService(db)
        result = await service.send_message(request=chat_request, user_id=current_user.id)

        return ResponseSchema(
            status="success",
            message="Message sent successfully",
            data=result.model_dump(),
        )

    except AIServiceError as e:
        logger.error(f"AI service error: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ResponseSchema(
                status="error",
                message="AI service encountered an error",
                data={"error": str(e)},
            ).model_dump(),
        )
    except Exception as e:
        logger.error(f"Unexpected error in chat: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ResponseSchema(
                status="error",
                message="An unexpected error occurred",
                data=None,
            ).model_dump(),
        )


@router.get("/conversations", response_model=ResponseSchema)
async def get_conversations(
    _request: Request,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all conversations for the current user.

    Args:
        page: Page number
        size: Page size
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of conversations with pagination
    """
    try:
        service = ChatService(db)
        result = await service.get_user_conversations(user_id=current_user.id, page=page, size=size)

        return ResponseSchema(
            status="success",
            message="Conversations retrieved successfully",
            data=result.model_dump(),
        )

    except Exception as e:
        logger.error(f"Error retrieving conversations: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ResponseSchema(
                status="error",
                message="Failed to retrieve conversations",
                data=None,
            ).model_dump(),
        )


@router.get("/conversations/{conversation_id}", response_model=ResponseSchema)
async def get_conversation(
    _request: Request,
    conversation_id: UUID = Path(..., description="Conversation ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific conversation with all messages.

    Args:
        conversation_id: Conversation ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Conversation with messages
    """
    try:
        service = ChatService(db)
        result = await service.get_conversation_history(conversation_id=conversation_id, user_id=current_user.id)

        return ResponseSchema(
            status="success",
            message="Conversation retrieved successfully",
            data=result.model_dump(),
        )

    except ValueError as e:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=ResponseSchema(
                status="error",
                message=str(e),
                data=None,
            ).model_dump(),
        )
    except Exception as e:
        logger.error(f"Error retrieving conversation: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ResponseSchema(
                status="error",
                message="Failed to retrieve conversation",
                data=None,
            ).model_dump(),
        )


@router.delete("/conversations/{conversation_id}", response_model=ResponseSchema)
async def delete_conversation(
    _request: Request,
    conversation_id: UUID = Path(..., description="Conversation ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a conversation.

    Args:
        conversation_id: Conversation ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Success response
    """
    try:
        service = ChatService(db)
        await service.delete_conversation(conversation_id=conversation_id, user_id=current_user.id)

        return ResponseSchema(
            status="success",
            message="Conversation deleted successfully",
            data=None,
        )

    except ValueError as e:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=ResponseSchema(
                status="error",
                message=str(e),
                data=None,
            ).model_dump(),
        )
    except Exception as e:
        logger.error(f"Error deleting conversation: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ResponseSchema(
                status="error",
                message="Failed to delete conversation",
                data=None,
            ).model_dump(),
        )
