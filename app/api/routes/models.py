"""Model management API routes."""
from fastapi import APIRouter, HTTPException

from app.models.schemas import ModelListResponse, ModelInfo
from app.core.ollama_cluster import ollama_cluster
from app.logging_config import log

router = APIRouter(prefix="/models", tags=["models"])


@router.get("", response_model=ModelListResponse)
async def list_models():
    """List all available models across all servers."""
    try:
        servers = ollama_cluster.get_server_info()
        models = []

        for server in servers:
            for model_name in server.get("loaded_models", []):
                models.append(ModelInfo(
                    name=model_name,
                    server=server["name"],
                    status="healthy" if server["is_healthy"] else "unhealthy",
                    capabilities=["chat", "completion"],
                    context_length=8192,
                    loaded=True
                ))

        return ModelListResponse(
            models=models,
            total=len(models)
        )
    except Exception as e:
        log.error(f"Failed to list models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{model_name}")
async def get_model_info(model_name: str):
    """Get information about a specific model."""
    servers = ollama_cluster.get_server_info()

    for server in servers:
        if model_name in server.get("loaded_models", []):
            return {
                "name": model_name,
                "server": server["name"],
                "status": "healthy" if server["is_healthy"] else "unhealthy",
                "capabilities": ["chat", "completion"],
                "context_length": 8192
            }

    raise HTTPException(status_code=404, detail=f"Model {model_name} not found")


@router.get("/servers/status")
async def get_servers_status():
    """Get status of all Ollama servers."""
    try:
        servers = ollama_cluster.get_server_info()
        return {"servers": servers, "total": len(servers)}
    except Exception as e:
        log.error(f"Failed to get server status: {e}")
        raise HTTPException(status_code=500, detail=str(e))