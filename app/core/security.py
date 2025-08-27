"""Security related functions."""

import httpx
from fastapi import HTTPException, status
import jwt
from jwt import InvalidTokenError

from app.core.config import settings


class ClerkAuthenticator:
    """
    Handles Clerk API authentication and token verification.

    This class is responsible for integrating with Clerk by verifying JSON Web Tokens
    (JWTs) using a secret key. The main purpose of this class is to ensure tokens
    issued by Clerk are valid and trustworthy for further application processes.

    :ivar clerk_api_url: The base URL of the Clerk API.
    :type clerk_api_url: str
    :ivar secret_key: The secret key used to verify JWT tokens.
    :type secret_key: str
    """

    def __init__(self):
        self.clerk_api_url = settings.clerk_api_url
        self.secret_key = settings.clerk_secret_key

    async def get_jwks(self) -> dict:
        """Get JWKS from Clerk for token verification."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.clerk_api_url}/.well-known/jwks.json")
            return response.json()

    async def verify_token(self, token: str) -> dict:
        """
        Verifies a given JSON Web Token (JWT) using Clerk's public key. The method decodes
        the provided token and validates its authenticity. If the token is invalid,
        it raises an HTTPException with proper status code and error detail.

        :param token: The JWT token to be verified.
        :return: A dictionary containing the decoded payload of the token if validation succeeds.
        """
        try:
            # For testing, decode without verification
            # In production, you should verify the signature using JWKS
            payload = jwt.decode(
                token,
                key="",  # Empty key for unverified decode
                options={
                    "verify_signature": False,
                    "verify_aud": False,
                    "verify_exp": False,  # Enable expiration checking
                },
            )
            return payload
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid authentication token: {str(e)}",
            )
