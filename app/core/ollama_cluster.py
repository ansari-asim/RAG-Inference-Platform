"""Ollama cluster management - handles multiple Ollama servers."""
import httpx
import asyncio
from typing import List, Dict, Any, Optional, AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
import json

from app.config import settings
from app.logging_config import log
from app.exceptions import OllamaConnectionException


@dataclass
class OllamaServer:
    """Represents a single Ollama server."""
    url: str
    name: str
    is_healthy: bool = True
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_check: Optional[datetime] = None
    response_time_ms: float = 0.0
    loaded_models: List[str] = field(default_factory=list)
    max_load: int = 10
    current_load: int = 0
    weight: float = 1.0


class OllamaCluster:
    """Manages a cluster of Ollama servers."""

    def __init__(self):
        self.servers: Dict[str, OllamaServer] = {}
        self._init_servers()

    def _init_servers(self):
        """Initialize servers from configuration."""
        server_urls = settings.get_ollama_servers()
        for i, url in enumerate(server_urls):
            server_name = f"server-{chr(65 + i)}"  # server-a, server-b, etc.
            self.servers[url] = OllamaServer(
                url=url,
                name=server_name,
                weight=1.0
            )
        log.info(f"Initialized {len(self.servers)} Ollama servers")

    async def check_server_health(self, server_url: str) -> bool:
        """Check if a server is healthy."""
        try:
            async with httpx.AsyncClient(
                timeout=settings.health_check_timeout
            ) as client:
                start_time = datetime.utcnow()
                response = await client.get(f"{server_url}/api/tags")
                response_time = (datetime.utcnow() - start_time).total_seconds() * 1000

                if response.status_code == 200:
                    server = self.servers.get(server_url)
                    if server:
                        server.is_healthy = True
                        server.response_time_ms = response_time
                        server.last_check = datetime.utcnow()
                        server.consecutive_failures = 0
                        server.consecutive_successes += 1

                        # Get available models
                        try:
                            data = response.json()
                            server.loaded_models = [
                                m.get("name", "") for m in data.get("models", [])
                            ]
                        except:
                            pass

                    return True
                return False
        except Exception as e:
            log.warning(f"Health check failed for {server_url}: {e}")
            server = self.servers.get(server_url)
            if server:
                server.is_healthy = False
                server.consecutive_failures += 1
                server.consecutive_successes = 0
            return False

    async def check_all_servers(self):
        """Check health of all servers."""
        tasks = [
            self.check_server_health(url)
            for url in self.servers.keys()
        ]
        await asyncio.gather(*tasks)

    async def get_embeddings(
        self,
        texts: List[str],
        server_url: Optional[str] = None
    ) -> List[List[float]]:
        """Generate embeddings for texts."""
        if server_url:
            return await self._generate_embeddings_single(texts, server_url)
        else:
            # Try all healthy servers
            for url in self.servers.keys():
                if self.servers[url].is_healthy:
                    try:
                        return await self._generate_embeddings_single(texts, url)
                    except Exception as e:
                        log.warning(f"Embedding generation failed on {url}: {e}")
                        continue
            raise OllamaConnectionException("all", "Failed to generate embeddings")

    async def _generate_embeddings_single(
        self,
        texts: List[str],
        server_url: str
    ) -> List[List[float]]:
        """Generate embeddings from a single server."""
        embeddings = []
        async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
            for text in texts:
                response = await client.post(
                    f"{server_url}/api/embeddings",
                    json={
                        "model": settings.embedding_model,
                        "prompt": text
                    }
                )
                response.raise_for_status()
                result = response.json()
                embeddings.append(result.get("embedding", []))
        return embeddings

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str,
        server_url: Optional[str] = None,
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """Send chat request to Ollama."""
        target_url = server_url or self._get_server_for_model(model)

        if not target_url:
            raise OllamaConnectionException("all", "No healthy servers available")

        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "temperature": temperature
        }

        if max_tokens:
            payload["options"] = {"num_predict": max_tokens}

        async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
            response = await client.post(
                f"{target_url}/api/chat",
                json=payload
            )
            response.raise_for_status()
            return response.json()

    async def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: str,
        server_url: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> AsyncIterator[str]:
        """Send streaming chat request to Ollama."""
        target_url = server_url or self._get_server_for_model(model)

        if not target_url:
            raise OllamaConnectionException("all", "No healthy servers available")

        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            "temperature": temperature
        }

        if max_tokens:
            payload["options"] = {"num_predict": max_tokens}

        async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
            async with client.stream(
                "POST",
                f"{target_url}/api/chat",
                json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            yield data.get("message", {}).get("content", "")
                            if data.get("done", False):
                                break
                        except json.JSONDecodeError:
                            continue

    def _get_server_for_model(self, model: str) -> Optional[str]:
        """Get server URL for a specific model based on mapping."""
        mapping = settings.get_model_server_mapping()

        # Check explicit mapping
        if model in mapping:
            server_name = mapping[model]
            for url, server in self.servers.items():
                if server.name == server_name and server.is_healthy:
                    return url

        # Fallback to load balancer
        return self.get_best_server()

    def get_best_server(self) -> Optional[str]:
        """Get the best available server using load balancing."""
        healthy_servers = [
            (url, server) for url, server in self.servers.items()
            if server.is_healthy and server.current_load < server.max_load
        ]

        if not healthy_servers:
            # Return any server if all are unhealthy
            if self.servers:
                return list(self.servers.keys())[0]
            return None

        strategy = settings.load_balancing_strategy

        if strategy == "least_load":
            return min(healthy_servers, key=lambda x: x[1].current_load)[0]
        elif strategy == "weighted":
            # Weighted random selection
            total_weight = sum(s.weight for _, s in healthy_servers)
            import random
            r = random.uniform(0, total_weight)
            cumulative = 0
            for url, server in healthy_servers:
                cumulative += server.weight
                if cumulative >= r:
                    return url
            return healthy_servers[0][0]
        else:  # round_robin
            for url, server in healthy_servers:
                if server.current_load == 0:
                    return url
            return healthy_servers[0][0]

    def get_server_info(self) -> List[Dict[str, Any]]:
        """Get info about all servers."""
        return [
            {
                "url": url,
                "name": server.name,
                "is_healthy": server.is_healthy,
                "response_time_ms": server.response_time_ms,
                "loaded_models": server.loaded_models,
                "current_load": server.current_load,
                "max_load": server.max_load,
                "weight": server.weight,
                "last_check": server.last_check.isoformat() if server.last_check else None
            }
            for url, server in self.servers.items()
        ]

    def get_healthy_servers(self) -> List[str]:
        """Get list of healthy server URLs."""
        return [
            url for url, server in self.servers.items()
            if server.is_healthy
        ]

    async def increment_load(self, server_url: str):
        """Increment load on a server."""
        if server_url in self.servers:
            self.servers[server_url].current_load += 1

    async def decrement_load(self, server_url: str):
        """Decrement load on a server."""
        if server_url in self.servers:
            self.servers[server_url].current_load = max(
                0, self.servers[server_url].current_load - 1
            )


# Global cluster instance
ollama_cluster = OllamaCluster()