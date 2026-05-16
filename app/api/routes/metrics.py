"""Metrics API routes."""
from fastapi import APIRouter

from app.models.schemas import MetricsResponse
from app.services.metrics_service import metrics_service
from app.logging_config import log

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("", response_model=MetricsResponse)
async def get_metrics():
    """Get current application metrics."""
    try:
        metrics = await metrics_service.get_metrics()
        return MetricsResponse(**metrics)
    except Exception as e:
        log.error(f"Failed to get metrics: {e}")
        return MetricsResponse(
            total_requests=0,
            active_requests=0,
            successful_requests=0,
            failed_requests=0,
            avg_response_time_ms=0.0,
            total_tokens=0,
            cache_hit_rate=0.0,
            server_load={}
        )


@router.post("/reset")
async def reset_metrics():
    """Reset all metrics."""
    await metrics_service.reset()
    return {"message": "Metrics reset successfully"}