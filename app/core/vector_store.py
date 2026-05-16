"""Vector store service using ChromaDB."""
import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any, Optional
import uuid

from app.config import settings
from app.logging_config import log
from app.core.ollama_client import ollama_client


class VectorStore:
    """ChromaDB-based vector store for RAG."""

    def __init__(
        self,
        persist_path: str = None,
        collection_name: str = None
    ):
        self.persist_path = persist_path or settings.chroma_persistence_path
        self.collection_name = collection_name or settings.chroma_collection_name
        self.client = None
        self.collection = None

    def init(self):
        """Initialize ChromaDB client and collection."""
        try:
            self.client = chromadb.PersistentClient(
                path=self.persist_path,
                settings=ChromaSettings(anonymized_telemetry=False)
            )

            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )

            log.info(f"Vector store initialized with collection: {self.collection_name}")
            log.info(f"Collection contains {self.collection.count()} items")

        except Exception as e:
            log.error(f"Failed to initialize vector store: {e}")
            raise

    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
        embeddings: Optional[List[List[float]]] = None,
        ids: Optional[List[str]] = None
    ) -> List[str]:
        """
        Add documents to the vector store.

        Args:
            documents: List of dicts with 'content' and 'metadata'
            embeddings: Pre-computed embeddings (optional)
            ids: Custom IDs (optional, will generate if not provided)

        Returns:
            List of document IDs
        """
        if not documents:
            return []

        try:
            # Generate IDs if not provided
            if ids is None:
                ids = [str(uuid.uuid4()) for _ in documents]

            # Extract content and metadata
            contents = [doc.get('content', '') for doc in documents]
            metadatas = [doc.get('metadata', {}) for doc in documents]

            # Generate embeddings if not provided
            if embeddings is None:
                log.info(f"Generating embeddings for {len(documents)} documents")
                embeddings = await ollama_client.get_embeddings(contents)

            # Add to collection
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=contents,
                metadatas=metadatas
            )

            log.info(f"Added {len(documents)} documents to vector store")
            return ids

        except Exception as e:
            log.error(f"Failed to add documents: {e}")
            raise

    async def search(
        self,
        query: str,
        k: int = 5,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search the vector store for relevant documents.

        Args:
            query: Search query text
            k: Number of results to return
            filter: Metadata filter (optional)

        Returns:
            List of matching documents with scores
        """
        try:
            # Generate query embedding
            query_embedding = await ollama_client.get_embeddings([query])
            query_embedding = query_embedding[0]

            # Search
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                where=filter,
                include=["documents", "metadatas", "distances"]
            )

            # Format results
            formatted_results = []
            if results and results.get('ids'):
                for i in range(len(results['ids'][0])):
                    formatted_results.append({
                        'id': results['ids'][0][i],
                        'content': results['documents'][0][i],
                        'score': 1 - results['distances'][0][i],  # Convert distance to similarity
                        'metadata': results['metadatas'][0][i] if results.get('metadatas') else {}
                    })

            log.info(f"Found {len(formatted_results)} results for query: {query[:50]}...")
            return formatted_results

        except Exception as e:
            log.error(f"Failed to search vector store: {e}")
            raise

    async def delete(
        self,
        ids: Optional[List[str]] = None,
        filter: Optional[Dict[str, Any]] = None
    ):
        """
        Delete documents from the vector store.

        Args:
            ids: List of document IDs to delete
            filter: Metadata filter (optional)
        """
        try:
            if ids:
                self.collection.delete(ids=ids)
                log.info(f"Deleted {len(ids)} documents by ID")
            elif filter:
                self.collection.delete(where=filter)
                log.info(f"Deleted documents matching filter: {filter}")
            else:
                log.warning("No IDs or filter provided for deletion")

        except Exception as e:
            log.error(f"Failed to delete documents: {e}")
            raise

    async def count(self) -> int:
        """Get the number of documents in the collection."""
        try:
            return self.collection.count()
        except Exception as e:
            log.error(f"Failed to count documents: {e}")
            return 0

    async def get_by_id(self, ids: List[str]) -> List[Dict[str, Any]]:
        """Get documents by their IDs."""
        try:
            results = self.collection.get(
                ids=ids,
                include=["documents", "metadatas"]
            )

            documents = []
            if results and results.get('ids'):
                for i in range(len(results['ids'])):
                    documents.append({
                        'id': results['ids'][i],
                        'content': results['documents'][i],
                        'metadata': results['metadatas'][i] if results.get('metadatas') else {}
                    })

            return documents

        except Exception as e:
            log.error(f"Failed to get documents by ID: {e}")
            raise

    def close(self):
        """Close the vector store client."""
        # ChromaDB doesn't require explicit closing
        log.info("Vector store closed")


# Global instance
vector_store = VectorStore()