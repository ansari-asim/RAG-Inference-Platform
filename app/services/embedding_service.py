"""Embedding service for generating embeddings."""
from typing import List

from app.core.ollama_cluster import ollama_cluster
from app.logging_config import log


class EmbeddingService:
    """Service for generating embeddings."""

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        try:
            embeddings = await ollama_cluster.get_embeddings(texts)
            log.debug(f"Generated {len(embeddings)} embeddings")
            return embeddings
        except Exception as e:
            log.error(f"Embedding generation failed: {e}")
            raise

    async def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a single query."""
        embeddings = await self.embed_texts([query])
        return embeddings[0] if embeddings else []


# Global instance
embedding_service = EmbeddingService()