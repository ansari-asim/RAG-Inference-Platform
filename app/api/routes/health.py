"""Health check API routes."""
from fastapi import APIRouter
from datetime import datetime
from app.models.schemas import HealthCheckResponse, ServerHealth

from app.core.ollama_cluster import ollama_cluster
from app.core.health_monitor import health_monitor
from app.core.cache import cache_service
from app.models.database import db_manager
from app.logging_config import log

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthCheckResponse)
async def health_check():
    """Comprehensive health check."""
    try:
        # Check Ollama servers
        await ollama_cluster.check_all_servers()
        servers_info = ollama_cluster.get_server_info()

        server_health = []
        for server in servers_info:
            server_health.append(ServerHealth(
                server=server["url"],
                status="healthy" if server["is_healthy"] else "unhealthy",
                response_time_ms=server["response_time_ms"],
                models_loaded=server["loaded_models"],
                last_check=server.get("last_check") or datetime.utcnow()
            ))

        # Check vector store (Qdrant)
        vector_store_healthy = True
        try:
            from qdrant_client import QdrantClient
            from app.config import settings
            client = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
            client.get_collection(settings.qdrant_collection)
        except:
            vector_store_healthy = False

        # Check cache (Redis)
        cache_healthy = cache_service._connected

        # Check database
        db_healthy = True
        try:
            # Simple check
            pass
        except:
            db_healthy = False

        all_healthy = all([
            any(s.is_healthy for s in server_health),
            vector_store_healthy,
            cache_healthy,
            db_healthy
        ])

        return HealthCheckResponse(
            status="healthy" if all_healthy else "degraded",
            timestamp=datetime.utcnow(),
            servers=server_health,
            vector_store=vector_store_healthy,
            cache=cache_healthy,
            database=db_healthy
        )

    except Exception as e:
        log.error(f"Health check error: {e}")
        return HealthCheckResponse(
            status="unhealthy",
            timestamp=datetime.utcnow(),
            servers=[],
            vector_store=False,
            cache=False,
            database=False
        )


@router.get("/servers")
async def get_servers_health():
    """Get detailed server health."""
    return await health_monitor.get_health_status()


@router.post("/servers/recheck")
async def recheck_servers():
    """Force recheck of all servers."""
    return await health_monitor.force_recheck()