"""Context injection middleware for prompt engineering."""
from fastapi import Request
from typing import Optional

from app.logging_config import log


class ContextInjectionMiddleware:
    """Middleware for injecting context into requests."""

    async def inject_context(self, request: Request, body: dict) -> dict:
        """Inject context into request body."""
        # This would inject retrieved memories and context
        # The actual injection happens in the chat endpoint
        return body


context_injection = ContextInjectionMiddleware()