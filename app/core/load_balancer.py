"""Load balancer for Ollama servers."""
from typing import Optional
import random

from app.logging_config import log
from app.core.ollama_cluster import ollama_cluster


class LoadBalancer:
    """Load balancing across Ollama servers."""

    @staticmethod
    def get_server(
        model: Optional[str] = None,
        strategy: str = "weighted"
    ) -> Optional[str]:
        """
        Get the best server based on strategy.

        Args:
            model: Optional model name for routing
            strategy: Load balancing strategy

        Returns:
            Server URL or None
        """
        # First try model-specific routing
        if model:
            server_url = ollama_cluster._get_server_for_model(model)
            if server_url:
                return server_url

        # Fall back to load balancer
        return ollama_cluster.get_best_server()

    @staticmethod
    async def with_fallback(func, *args, **kwargs):
        """
        Execute a function with fallback to other servers on failure.

        Args:
            func: Async function to execute
            *args, **kwargs: Arguments for the function
        """
        from app.config import settings
        from app.exceptions import OllamaConnectionException

        fallback_servers = settings.get_fallback_servers()
        tried = set()

        for server in [ollama_cluster.get_best_server()] + fallback_servers:
            if server in tried:
                continue
            tried.add(server)

            try:
                return await func(*args, server_url=server, **kwargs)
            except Exception as e:
                log.warning(f"Request failed on {server}: {e}")
                continue

        raise OllamaConnectionException(
            "all",
            "All servers failed after retries"
        )