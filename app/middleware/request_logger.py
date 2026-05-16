"""Request/Response logging middleware."""
import time
import uuid
from fastapi import Request

from app.logging_config import log


class RequestLoggingMiddleware:
    """Middleware for logging requests and responses."""

    async def log_request(self, request: Request):
        """Log incoming request."""
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        log.info(
            f"[{request_id}] {request.method} {request.url.path} "
            f"- Client: {request.client.host}"
        )

        return request_id

    async def log_response(
        self,
        request_id: str,
        status_code: int,
        duration_ms: float
    ):
        """Log response."""
        log.info(
            f"[{request_id}] Response: {status_code} "
            f"- Duration: {duration_ms:.2f}ms"
        )


async def log_request_duration(request: Request, call_next):
    """Log request duration."""
    start_time = time.time()
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id

    response = await call_next(request)

    duration_ms = (time.time() - start_time) * 1000
    log.info(
        f"[{request_id}] {request.method} {request.url.path} "
        f"- Status: {response.status_code} - Duration: {duration_ms:.2f}ms"
    )

    return response