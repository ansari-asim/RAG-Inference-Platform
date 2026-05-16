"""Memory management API routes."""
from fastapi import APIRouter, HTTPException

from app.models.schemas import MemorySearchRequest, MemorySearchResponse, MemoryItem, MemoryStoreRequest
from app.services.memory_service import memory_service
from app.logging_config import log

router = APIRouter(prefix="/memory", tags=["memory"])


@router.post("/search", response_model=MemorySearchResponse)
async def search_memories(request: MemorySearchRequest):
    """Search for relevant memories."""
    try:
        results = await memory_service.retrieve_memories(
            query=request.query,
            user_id=request.user_id,
            k=request.k
        )

        memory_items = [
            MemoryItem(
                id=r["id"],
                content=r["content"],
                score=r["score"],
                metadata=r.get("metadata", {})
            )
            for r in results
        ]

        return MemorySearchResponse(
            query=request.query,
            results=memory_items,
            total=len(memory_items)
        )

    except Exception as e:
        log.error(f"Memory search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("")
async def store_memory(request: MemoryStoreRequest):
    """Store a new memory."""
    try:
        memory_id = await memory_service.store_memory(
            content=request.content,
            memory_type=request.memory_type,
            user_id=request.user_id,
            metadata=request.metadata
        )

        return {
            "success": bool(memory_id),
            "memory_id": memory_id,
            "message": "Memory stored successfully"
        }
    except Exception as e:
        log.error(f"Store memory error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("")
async def delete_memory(memory_id: str):
    """Delete a memory."""
    try:
        await memory_service.delete_memories(memory_ids=[memory_id])
        return {"success": True, "message": "Memory deleted"}
    except Exception as e:
        log.error(f"Delete memory error: {e}")
        raise HTTPException(status_code=500, detail=str(e))