"""Base exception classes."""

from fastapi import HTTPException
from typing import Optional, Dict, Any


class BaseAppException(HTTPException):
    """Base application exception."""
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        
        super().__init__(
            status_code=status_code,
            detail={
                "message": message,
                "error_code": error_code,
                "details": details
            }
        )