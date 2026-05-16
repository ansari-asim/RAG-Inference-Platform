"""Authentication middleware."""
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import hashlib

from app.config import settings
from app.logging_config import log

security = HTTPBearer()


class AuthMiddleware:
    """Authentication middleware."""

    async def verify_api_key(self, request: Request) -> Optional[dict]:
        """Verify API key from request."""
        # Check header
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            # Check query param for API key
            api_key = request.query_params.get("api_key")
            if api_key:
                return await self._verify_key(api_key)
            return None

        # Bearer token
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            return await self._verify_key(token)

        return None

    async def _verify_key(self, key: str) -> Optional[dict]:
        """Verify a single API key."""
        try:
            key_hash = hashlib.sha256(key.encode()).hexdigest()
            # In production, check against database
            return {"valid": True, "key_hash": key_hash}
        except Exception as e:
            log.error(f"Key verification failed: {e}")
            return None


auth_middleware = AuthMiddleware()


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """Dependency to get current user."""
    # In production, decode JWT and verify
    return {"user_id": "default"}


async def optional_auth(request: Request) -> Optional[dict]:
    """Optional authentication - returns None if not authenticated."""
    try:
        return await auth_middleware.verify_api_key(request)
    except:
        return None