"""Ollama client service for embeddings and chat."""
import httpx
from typing import List, Dict, Any, Optional, AsyncIterator
import json

from app.config import settings
from app.logging_config import log


class OllamaClient:
    """Client for interacting with Ollama API."""

    def __init__(self, base_url: str = None, embedding_model: str = None):
        self.base_url = base_url or settings.ollama_base_url
        self.embedding_model = embedding_model or settings.ollama_embedding_model
        self.model = settings.ollama_model
        self.client = httpx.AsyncClient(timeout=120.0)

    async def check_connection(self) -> bool:
        """Check if Ollama is running and accessible."""
        try:
            response = await self.client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception as e:
            log.error(f"Ollama connection check failed: {e}")
            return False

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for texts using Ollama.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors
        """
        embeddings = []

        try:
            for text in texts:
                response = await self.client.post(
                    f"{self.base_url}/api/embeddings",
                    json={
                        "model": self.embedding_model,
                        "prompt": text
                    }
                )
                response.raise_for_status()
                result = response.json()
                embeddings.append(result.get("embedding", []))
                log.debug(f"Generated embedding for text of length {len(text)}")

            log.info(f"Generated {len(embeddings)} embeddings")
            return embeddings

        except httpx.HTTPStatusError as e:
            log.error(f"HTTP error generating embeddings: {e.response.status_code}")
            raise
        except Exception as e:
            log.error(f"Error generating embeddings: {e}")
            raise

    async def generate(
        self,
        prompt: str,
        model: str = None,
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        context: Optional[List[int]] = None
    ) -> AsyncIterator[str] | Dict[str, Any]:
        """
        Generate text completion from Ollama.

        Args:
            prompt: The prompt to generate from
            model: Model name (optional, uses default)
            stream: Enable streaming
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            context: Context window for generation

        Yields (if streaming):
            Generated text chunks

        Returns (if not streaming):
            Full response dict
        """
        model = model or self.model

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "temperature": temperature,
        }

        if max_tokens:
            payload["options"] = {"num_predict": max_tokens}
        if context:
            payload["context"] = context

        try:
            if stream:
                async with self.client.stream(
                    "POST",
                    f"{self.base_url}/api/generate",
                    json=payload
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                yield data.get("response", "")
                                if data.get("done", False):
                                    break
                            except json.JSONDecodeError:
                                continue
            else:
                response = await self.client.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPStatusError as e:
            log.error(f"HTTP error in generation: {e.response.status_code}")
            raise
        except Exception as e:
            log.error(f"Error in generation: {e}")
            raise

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Send a chat completion request to Ollama.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model name
            stream: Enable streaming
            temperature: Sampling temperature
            max_tokens: Max tokens

        Returns:
            Response dict with message and metadata
        """
        model = model or self.model

        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "temperature": temperature
        }

        if max_tokens:
            payload["options"] = {"num_predict": max_tokens}

        try:
            response = await self.client.post(
                f"{self.base_url}/api/chat",
                json=payload
            )
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            log.error(f"HTTP error in chat: {e.response.status_code}")
            raise
        except Exception as e:
            log.error(f"Error in chat: {e}")
            raise

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
        log.info("Ollama client closed")


# Global client instance
ollama_client = OllamaClient()