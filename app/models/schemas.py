"""Pydantic schemas for request/response validation."""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    """Message role enum."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class StreamMode(str, Enum):
    """Stream mode enum."""
    STREAM = "stream"
    NON_STREAM = "non_stream"


# ============== Chat Schemas ==============

class ChatMessage(BaseModel):
    """Individual chat message."""
    role: str = Field(..., description="Message role: 'system', 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """Request schema for chat endpoint."""
    messages: List[ChatMessage] = Field(..., description="List of chat messages")
    model: Optional[str] = Field(None, description="Model name")
    stream: Optional[bool] = Field(False, description="Enable streaming")
    session_id: Optional[str] = Field(None, description="Session identifier")
    temperature: Optional[float] = Field(0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: Optional[int] = Field(None, gt=0, description="Max tokens to generate")
    top_p: Optional[float] = Field(1.0, ge=0.0, le=1.0, description="Nucleus sampling")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class ChatResponse(BaseModel):
    """Response schema for chat endpoint."""
    model: str
    message: ChatMessage
    done: bool
    session_id: Optional[str] = None
    retrieved_memories: Optional[List[Dict[str, Any]]] = None
    context_used: bool = False
    response_time_ms: Optional[float] = None
    tokens_used: Optional[int] = None


class ChatStreamChunk(BaseModel):
    """Streaming chat response chunk."""
    model: str
    content: str
    done: bool
    session_id: Optional[str] = None


# ============== Document Schemas ==============

class DocumentIngestRequest(BaseModel):
    """Request to ingest a document."""
    content: str = Field(..., min_length=1, description="Document content")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Document metadata")
    doc_type: str = Field("general", description="Document type")
    source: Optional[str] = Field(None, description="Document source")
    user_id: Optional[str] = Field(None, description="User ID")


class DocumentIngestResponse(BaseModel):
    """Response after document ingestion."""
    success: bool
    chunks_created: int
    document_id: str
    message: str


# ============== Memory Schemas ==============

class MemorySearchRequest(BaseModel):
    """Request to search memories."""
    query: str = Field(..., min_length=1, description="Search query")
    k: int = Field(5, ge=1, le=100, description="Number of results")
    filter: Optional[Dict[str, Any]] = Field(None, description="Metadata filter")
    user_id: Optional[str] = Field(None, description="Filter by user")


class MemoryItem(BaseModel):
    """Individual memory item."""
    id: str
    content: str
    score: float
    metadata: Dict[str, Any]


class MemorySearchResponse(BaseModel):
    """Response with retrieved memories."""
    query: str
    results: List[MemoryItem]
    total: int


class MemoryStoreRequest(BaseModel):
    """Request to store a memory."""
    content: str = Field(..., min_length=1, description="Memory content")
    memory_type: str = Field("general", description="Type of memory")
    user_id: Optional[str] = Field(None, description="User ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class MemoryDeleteRequest(BaseModel):
    """Request to delete memories."""
    memory_id: Optional[str] = None
    filter: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None


# ============== Model Management Schemas ==============

class ModelInfo(BaseModel):
    """Model information."""
    name: str
    server: str
    status: str
    capabilities: List[str]
    context_length: int
    loaded: bool = False


class ModelListResponse(BaseModel):
    """Response with list of models."""
    models: List[ModelInfo]
    total: int


class ServerHealth(BaseModel):
    """Server health status."""
    server: str
    status: str
    response_time_ms: float
    models_loaded: List[str]
    last_check: datetime


class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: datetime
    servers: List[ServerHealth]
    vector_store: bool
    cache: bool
    database: bool


# ============== User & Auth Schemas ==============

class UserCreate(BaseModel):
    """User creation request."""
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    """User login request."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response."""
    access_token: str
    token_type: str
    expires_in: int


class UserResponse(BaseModel):
    """User response."""
    id: str
    username: str
    email: str
    full_name: Optional[str]
    is_active: bool
    created_at: datetime


# ============== Metrics Schemas ==============

class MetricsResponse(BaseModel):
    """Metrics response."""
    total_requests: int
    active_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time_ms: float
    total_tokens: int
    cache_hit_rate: float
    server_load: Dict[str, float]


# ============== Rate Limiting Schemas ==============

class RateLimitInfo(BaseModel):
    """Rate limit information."""
    limit: int
    remaining: int
    reset_at: datetime


# ============== Chat History Schemas ==============

class ChatHistoryEntry(BaseModel):
    """Single chat history entry."""
    id: int
    session_id: str
    user_message: str
    assistant_message: str
    model_used: str
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None


class ChatHistoryResponse(BaseModel):
    """Chat history response."""
    session_id: str
    messages: List[ChatHistoryEntry]
    total: int
    has_more: bool