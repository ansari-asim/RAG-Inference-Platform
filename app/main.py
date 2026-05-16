"""FastAPI application entry point."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.logging_config import log
from app.models.database import db_manager
from app.core.ollama_cluster import ollama_cluster
from app.core.health_monitor import health_monitor
from app.core.cache import cache_service
from app.middleware.rate_limiter import RateLimiterMiddleware
from app.middleware.request_logger import log_request_duration

# Import routers
from app.api.routes import chat, models, documents, memory, health, metrics


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown."""
    log.info("=" * 60)
    log.info("Starting RAG Inference Platform...")
    log.info("=" * 60)

    # Initialize database
    await db_manager.init()
    log.info("Database initialized")

    # Connect to Redis
    await cache_service.connect()
    log.info("Redis cache connected")

    # Initialize Ollama cluster
    await ollama_cluster.check_all_servers()
    log.info(f"Ollama cluster initialized with {len(ollama_cluster.servers)} servers")

    # Start health monitoring
    await health_monitor.start()
    log.info("Health monitoring started")

    log.info(f"API available at http://{settings.api_host}:{settings.api_port}{settings.api_prefix}")
    log.info(f"API docs at http://{settings.api_host}:{settings.api_port}/docs")
    log.info("=" * 60)

    yield

    # Shutdown
    log.info("Shutting down RAG Inference Platform...")
    await health_monitor.stop()
    await cache_service.disconnect()
    await db_manager.close()
    log.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="RAG Inference Platform",
    description="Distributed RAG + Multi-LLM Inference Platform",
    version="1.0.0",
    lifespan=lifespan
)

# Add middleware
if settings.rate_limit_enabled:
    app.add_middleware(RateLimiterMiddleware)

app.middleware("http")(log_request_duration)

# Configure CORS
cors_origins = settings.cors_origins.split(",") if settings.cors_origins != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix=settings.api_prefix)
app.include_router(models.router, prefix=settings.api_prefix)
app.include_router(documents.router, prefix=settings.api_prefix)
app.include_router(memory.router, prefix=settings.api_prefix)
app.include_router(health.router, prefix=settings.api_prefix)
app.include_router(metrics.router, prefix=settings.api_prefix)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "api_prefix": settings.api_prefix,
        "status": "running"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    log.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )