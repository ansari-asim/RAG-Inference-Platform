"""RAG pipeline service for document processing and retrieval."""
from typing import List, Dict, Any, Optional
import hashlib

from app.config import settings
from app.logging_config import log
from app.core.ollama_cluster import ollama_cluster
from app.utils.text_chunker import TextChunker


class RAGPipeline:
    """Handles the complete RAG pipeline."""

    def __init__(self):
        self.chunker = TextChunker()

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for texts."""
        try:
            embeddings = await ollama_cluster.get_embeddings(texts)
            return embeddings
        except Exception as e:
            log.error(f"Failed to generate embeddings: {e}")
            raise

    async def ingest_document(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        doc_type: str = "general",
        source: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Ingest a document into the vector store."""
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams, PointStruct
            from uuid import uuid4

            # Prepare metadata
            doc_metadata = metadata or {}
            doc_metadata.update({
                "doc_type": doc_type,
                "source": source,
                "user_id": user_id
            })

            # Chunk the document
            chunks = self.chunker.chunk_text(content)

            if not chunks:
                return {
                    "success": False,
                    "chunks_created": 0,
                    "document_id": None,
                    "message": "No content to ingest"
                }

            # Generate embeddings
            embeddings = await self.generate_embeddings(chunks)

            # Connect to Qdrant
            client = QdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port
            )

            # Ensure collection exists
            try:
                client.get_collection(settings.qdrant_collection)
            except:
                client.create_collection(
                    settings.qdrant_collection,
                    vectors_config=VectorParams(
                        size=settings.qdrant_vector_size,
                        distance=Distance.COSINE
                    )
                )

            # Create points
            points = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                point_id = str(uuid4())
                points.append(
                    PointStruct(
                        id=point_id,
                        vector=embedding,
                        payload={
                            "content": chunk,
                            "chunk_index": i,
                            "total_chunks": len(chunks),
                            **doc_metadata
                        }
                    )
                )

            # Insert into Qdrant
            client.upsert(
                collection_name=settings.qdrant_collection,
                points=points
            )

            document_id = points[0].id
            log.info(f"Ingested document with {len(chunks)} chunks, ID: {document_id}")

            return {
                "success": True,
                "chunks_created": len(chunks),
                "document_id": document_id,
                "message": f"Successfully created {len(chunks)} chunks"
            }

        except Exception as e:
            log.error(f"Failed to ingest document: {e}")
            return {
                "success": False,
                "chunks_created": 0,
                "document_id": None,
                "message": str(e)
            }

    async def retrieve_context(
        self,
        query: str,
        k: int = None,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant context for a query."""
        k = k or settings.top_k_memories

        try:
            from qdrant_client import QdrantClient

            # Generate query embedding
            query_embedding = await self.generate_embeddings([query])
            query_embedding = query_embedding[0]

            # Connect to Qdrant
            client = QdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port
            )

            # Build filter
            from qdrant_client.models import Filter, FieldCondition, Match
            must_conditions = []
            if user_id:
                must_conditions.append(
                    FieldCondition(key="user_id", match=Match(value=user_id))
                )

            filter_obj = Filter(must=must_conditions) if must_conditions else None

            # Search
            results = client.search(
                collection_name=settings.qdrant_collection,
                query_vector=query_embedding,
                limit=k,
                score_threshold=settings.similarity_threshold,
                query_filter=filter_obj
            )

            # Format results
            formatted = [
                {
                    "id": r.id,
                    "content": r.payload.get("content", ""),
                    "score": r.score,
                    "metadata": {
                        k: v for k, v in r.payload.items()
                        if k != "content"
                    }
                }
                for r in results
            ]

            log.info(f"Retrieved {len(formatted)} context documents")
            return formatted

        except Exception as e:
            log.error(f"Failed to retrieve context: {e}")
            return []

    async def augment_prompt(
        self,
        user_query: str,
        retrieved_context: List[Dict[str, Any]],
        conversation_history: str = "",
        system_prompt: Optional[str] = None
    ) -> str:
        """Augment user query with retrieved context."""
        # Build context section
        context_section = ""
        if retrieved_context:
            context_section = "## Relevant Context\n\n"
            for i, doc in enumerate(retrieved_context, 1):
                context_section += f"{i}. {doc.get('content', '')}\n\n"

        # Build history section
        history_section = ""
        if conversation_history:
            history_section = f"## Previous Conversation\n\n{conversation_history}\n\n"

        # Build system prompt
        if system_prompt:
            base_system = system_prompt
        else:
            base_system = """You are a helpful AI assistant with access to contextual information.
Use the provided context to answer questions accurately. If the context doesn't contain
relevant information, rely on your general knowledge."""

        # Combine
        augmented = f"{base_system}\n\n{context_section}{history_section}## Current Query\n\n{user_query}"

        # Truncate if too long
        max_chars = settings.max_context_length * 4
        if len(augmented) > max_chars:
            augmented = augmented[:max_chars] + "\n\n[Context truncated]"

        return augmented


# Global instance
rag_pipeline = RAGPipeline()