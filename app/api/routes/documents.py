"""Document ingestion API routes."""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import Optional
import json

from app.models.schemas import DocumentIngestRequest, DocumentIngestResponse
from app.services.rag_pipeline import rag_pipeline
from app.logging_config import log

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/ingest", response_model=DocumentIngestResponse)
async def ingest_document(request: DocumentIngestRequest):
    """Ingest a document into the RAG system."""
    try:
        log.info(f"Ingesting document of type: {request.doc_type}")

        result = await rag_pipeline.ingest_document(
            content=request.content,
            metadata=request.metadata,
            doc_type=request.doc_type,
            source=request.source,
            user_id=request.user_id
        )

        if result["success"]:
            return DocumentIngestResponse(
                success=True,
                chunks_created=result["chunks_created"],
                document_id=result["document_id"],
                message=result["message"]
            )
        else:
            raise HTTPException(status_code=500, detail=result["message"])

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Document ingestion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest/file")
async def ingest_file(
    file: UploadFile = File(...),
    doc_type: str = Form("general"),
    source: str = Form(None),
    metadata_json: str = Form("{}")
):
    """Ingest a file into the RAG system."""
    try:
        metadata = json.loads(metadata_json)
        metadata["filename"] = file.filename

        content = await file.read()
        if file.filename.endswith('.txt'):
            content = content.decode('utf-8')
        else:
            content = f"File: {file.filename} (content type not supported)"

        result = await rag_pipeline.ingest_document(
            content=content,
            metadata=metadata,
            doc_type=doc_type,
            source=source or file.filename
        )

        return DocumentIngestResponse(
            success=result["success"],
            chunks_created=result["chunks_created"],
            document_id=result["document_id"],
            message=result["message"]
        )

    except Exception as e:
        log.error(f"File ingestion error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/count")
async def get_document_count():
    """Get approximate document count."""
    return {"message": "Use Qdrant API for exact count", "collection": "rag_memories"}