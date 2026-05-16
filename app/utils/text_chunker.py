"""Text chunking utilities for document processing."""
from typing import List
import re

from app.config import settings
from app.logging_config import log


class TextChunker:
    """Handles text chunking for RAG pipeline."""

    def __init__(self, chunk_size: int = None, chunk_overlap: int = None):
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap

    def chunk_text(self, text: str) -> List[str]:
        """Split text into overlapping chunks."""
        if not text or not text.strip():
            return []

        # Clean text
        text = self._clean_text(text)

        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]

            # Try to break at sentence boundary
            if end < len(text):
                chunk = self._split_at_sentence_boundary(chunk)
                end = start + len(chunk)

            chunks.append(chunk.strip())
            start = end - self.chunk_overlap

        return [c for c in chunks if c.strip()]

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', text)
        return text.strip()

    def _split_at_sentence_boundary(self, text: str) -> str:
        """Split text at the nearest sentence boundary."""
        sentence_endings = r'[.!?]\s+'
        matches = list(re.finditer(sentence_endings, text))

        if matches:
            return text[:matches[-1].end()]

        paragraphs = text.split('\n\n')
        if len(paragraphs) > 1:
            return paragraphs[0]

        last_space = text.rfind(' ')
        if last_space > len(text) * 0.8:
            return text[:last_space]

        return text

    def chunk_documents(self, documents: List[dict]) -> List[dict]:
        """Chunk multiple documents with metadata."""
        chunked_docs = []

        for doc in documents:
            content = doc.get('content', '')
            metadata = doc.get('metadata', {})
            chunks = self.chunk_text(content)

            for i, chunk in enumerate(chunks):
                chunk_meta = {
                    **metadata,
                    'chunk_index': i,
                    'total_chunks': len(chunks)
                }
                chunked_docs.append({
                    'content': chunk,
                    'metadata': chunk_meta
                })

        log.info(f"Chunked {len(documents)} documents into {len(chunked_docs)} chunks")
        return chunked_docs