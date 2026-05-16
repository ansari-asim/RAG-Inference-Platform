"""Chat API routes."""
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Optional
import uuid
import time

from app.models.schemas import ChatRequest, ChatResponse, ChatMessage, ChatHistoryResponse, ChatHistoryEntry
from app.core.ollama_cluster import ollama_cluster
from app.core.router import model_router
from app.services.rag_pipeline import rag_pipeline
from app.services.memory_service import memory_service
from app.services.chat_history_service import chat_history_service
from app.services.metrics_service import metrics_service
from app.config import settings
from app.logging_config import log
from app.middleware.auth import optional_auth

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    req: Request,
    user: Optional[dict] = Depends(optional_auth)
):
    """Main chat endpoint with RAG augmentation."""
    start_time = time.time()
    session_id = request.session_id or str(uuid.uuid4())

    # Extract user message
    user_message = ""
    for msg in reversed(request.messages):
        if msg.role == "user":
            user_message = msg.content
            break

    if not user_message:
        raise HTTPException(status_code=400, detail="No user message found")

    user_id = user.get("user_id") if user else None
    log.info(f"Chat request session={session_id}, model={request.model}")

    try:
        # 1. Route to appropriate model
        model = request.model or model_router.route(
            user_message,
            user_model_preference=None
        )

        # 2. Retrieve relevant memories
        memories = await memory_service.retrieve_memories(
            query=user_message,
            user_id=user_id,
            k=settings.top_k_memories
        )

        # 3. Get conversation history
        conversation_context = await chat_history_service.get_conversation_context(
            session_id=session_id,
            message_count=5
        )

        # 4. Build augmented prompt
        context_used = len(memories) > 0

        # Get system prompt based on context
        system_content = "You are a helpful AI assistant."
        if context_used:
            context_str = "\n\n".join([
                f"- {m['content']}" for m in memories[:3]
            ])
            system_content = f"""You are a helpful AI assistant with access to relevant context:

{context_str}

Previous conversation:
{conversation_context}"""

        # Build messages for Ollama
        ollama_messages = [{"role": "system", "content": system_content}]

        # Add recent history
        recent = await chat_history_service.get_recent_messages(session_id, 5)
        for msg in recent:
            ollama_messages.append({"role": "user", "content": msg.get("user_message", "")})
            ollama_messages.append({"role": "assistant", "content": msg.get("assistant_message", "")})

        # Add current message
        ollama_messages.append({"role": "user", "content": user_message})

        # 5. Send to Ollama
        response = await ollama_cluster.chat(
            messages=ollama_messages,
            model=model,
            stream=False,
            temperature=request.temperature or 0.7,
            max_tokens=request.max_tokens
        )

        assistant_message = response.get("message", {}).get("content", "")

        # 6. Save to history
        await chat_history_service.save_message(
            session_id=session_id,
            role="user",
            content=user_message,
            model_used=model,
            context_used=context_used
        )
        await chat_history_service.save_message(
            session_id=session_id,
            role="assistant",
            content=assistant_message,
            model_used=model,
            context_used=context_used
        )

        # 7. Record metrics
        response_time_ms = (time.time() - start_time) * 1000
        await metrics_service.record_request(
            model=model,
            server=settings.get_ollama_servers()[0],  # Would be actual server
            response_time_ms=response_time_ms,
            success=True,
            tokens_used=len(assistant_message.split())  # Approximate
        )

        return ChatResponse(
            model=model,
            message=ChatMessage(role="assistant", content=assistant_message),
            done=True,
            session_id=session_id,
            retrieved_memories=[
                {"id": m["id"], "score": m["score"], "content": m["content"][:200]}
                for m in memories
            ] if memories else None,
            context_used=context_used,
            response_time_ms=round(response_time_ms, 2)
        )

    except Exception as e:
        log.error(f"Chat error: {e}")
        response_time_ms = (time.time() - start_time) * 1000
        await metrics_service.record_request(
            model=request.model or settings.default_model,
            server="unknown",
            response_time_ms=response_time_ms,
            success=False,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{session_id}", response_model=ChatHistoryResponse)
async def get_chat_history(session_id: str, limit: int = 50):
    """Get chat history for a session."""
    try:
        messages = await chat_history_service.get_history(session_id, limit)
        return ChatHistoryResponse(
            session_id=session_id,
            messages=[
                ChatHistoryEntry(**m) for m in messages
            ],
            total=len(messages),
            has_more=len(messages) == limit
        )
    except Exception as e:
        log.error(f"Failed to get history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/history/{session_id}")
async def delete_chat_history(session_id: str):
    """Delete chat history for a session."""
    try:
        success = await chat_history_service.delete_session(session_id)
        if success:
            return {"message": "Session deleted", "session_id": session_id}
        raise HTTPException(status_code=500, detail="Failed to delete session")
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Delete history error: {e}")
        raise HTTPException(status_code=500, detail=str(e))