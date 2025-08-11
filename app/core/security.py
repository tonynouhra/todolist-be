"""Security related functions."""

from jose import JWTError, jwt
from fastapi import HTTPException, status
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
        self.clerk_api_url = settings.CLERK_API_URL
        self.secret_key = settings.CLERK_SECRET_KEY
    
    async def verify_token(self, token: str) -> dict:
        """
        Verifies a given JSON Web Token (JWT) using the secret key. The method decodes
        the provided token and validates its authenticity. If the token is invalid,
        it raises an HTTPException with proper status code and error detail.

        :param token: The JWT token to be verified.
        :return: A dictionary containing the decoded payload of the token if validation succeeds.
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"],options={"verify_aud": False})
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )
