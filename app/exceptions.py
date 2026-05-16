"""Custom exceptions for the application."""
from typing import Optional, Dict, Any


class RAGPlatformException(Exception):
    """Base exception for RAG platform."""

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class ModelNotFoundException(RAGPlatformException):
    """Raised when a model is not found."""

    def __init__(self, model_name: str):
        super().__init__(
            message=f"Model '{model_name}' not found",
            status_code=404,
            details={"model": model_name}
        )


class ServerUnavailableException(RAGPlatformException):
    """Raised when all Ollama servers are unavailable."""

    def __init__(self, servers: list):
        super().__init__(
            message="All Ollama servers are unavailable",
            status_code=503,
            details={"servers": servers}
        )


class OllamaConnectionException(RAGPlatformException):
    """Raised when connection to Ollama fails."""

    def __init__(self, server: str, reason: str):
        super().__init__(
            message=f"Failed to connect to Ollama server: {server}",
            status_code=502,
            details={"server": server, "reason": reason}
        )


class AuthenticationException(RAGPlatformException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            status_code=401,
            details={"error": "unauthorized"}
        )


class RateLimitException(RAGPlatformException):
    """Raised when rate limit is exceeded."""

    def __init__(self, limit: int, window: int):
        super().__init__(
            message=f"Rate limit exceeded. Limit: {limit} requests per {window} seconds",
            status_code=429,
            details={"limit": limit, "window": window}
        )


class VectorStoreException(RAGPlatformException):
    """Raised when vector store operation fails."""

    def __init__(self, operation: str, reason: str):
        super().__init__(
            message=f"Vector store error during {operation}: {reason}",
            status_code=500,
            details={"operation": operation, "reason": reason}
        )


class CacheException(RAGPlatformException):
    """Raised when cache operation fails."""

    def __init__(self, operation: str, reason: str):
        super().__init__(
            message=f"Cache error during {operation}: {reason}",
            status_code=500,
            details={"operation": operation, "reason": reason}
        )


class DatabaseException(RAGPlatformException):
    """Raised when database operation fails."""

    def __init__(self, operation: str, reason: str):
        super().__init__(
            message=f"Database error during {operation}: {reason}",
            status_code=500,
            details={"operation": operation, "reason": reason}
        )


class ValidationException(RAGPlatformException):
    """Raised when validation fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=422,
            details=details or {}
        )