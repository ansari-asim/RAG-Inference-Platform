"""Rate limiting middleware."""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime

from app.config import settings
from app.logging_config import log
from app.core.cache import cache_service


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware."""

    async def dispatch(self, request: Request, call_next):
        if not settings.rate_limit_enabled:
            return await call_next(request)

        # Get client identifier
        client_id = self._get_client_id(request)

        # Check rate limit
        allowed, remaining, reset_at = await cache_service.check_rate_limit(
            f"rate_limit:{client_id}",
            settings.rate_limit_requests,
            settings.rate_limit_window
        )

        if not allowed:
            log.warning(f"Rate limit exceeded for {client_id}")
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "Rate limit exceeded",
                    "limit": settings.rate_limit_requests,
                    "reset_at": reset_at
                }
            )

        # Add rate limit headers
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(settings.rate_limit_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_at)

        return response

    def _get_client_id(self, request: Request) -> str:
        """Get client identifier from request."""
        # Try API key
        auth_header = request.headers.get("Authorization")
        if auth_header:
            return f"api:{hash(auth_header)}"

        # Try IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0]}"

        return f"ip:{request.client.host}"