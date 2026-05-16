"""Memory service for managing long-term memory and retrieval."""
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.config import settings
from app.logging_config import log
from app.services.rag_pipeline import rag_pipeline


class MemoryService:
    """Manages user memory and context retrieval."""

    async def retrieve_memories(
        self,
        query: str,
        user_id: Optional[str] = None,
        k: int = None
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant memories for a query."""
        k = k or settings.top_k_memories

        try:
            memories = await rag_pipeline.retrieve_context(
                query=query,
                k=k,
                user_id=user_id
            )

            log.info(f"Retrieved {len(memories)} memories")
            return memories
        except Exception as e:
            log.error(f"Failed to retrieve memories: {e}")
            return []

    async def store_memory(
        self,
        content: str,
        memory_type: str = "general",
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Store a new memory."""
        try:
            result = await rag_pipeline.ingest_document(
                content=content,
                metadata=metadata,
                doc_type=memory_type,
                source="memory",
                user_id=user_id
            )

            if result["success"]:
                return result["document_id"]
            return ""
        except Exception as e:
            log.error(f"Failed to store memory: {e}")
            return ""

    async def search_memories(
        self,
        query: str,
        k: int = 5,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search memories directly."""
        return await self.retrieve_memories(query, user_id, k)

    async def delete_memories(
        self,
        memory_ids: Optional[List[str]] = None,
        user_id: Optional[str] = None
    ):
        """Delete memories."""
        # This would need implementation with Qdrant delete
        log.info(f"Deleting memories: {memory_ids}, user: {user_id}")


# Global instance
memory_service = MemoryService()