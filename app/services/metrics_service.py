"""Metrics service for collecting and reporting metrics."""
import time
import psutil
from typing import Dict, Any
from datetime import datetime
from collections import defaultdict

from app.logging_config import log
from app.core.cache import cache_service


class MetricsService:
    """Service for collecting application metrics."""

    def __init__(self):
        self._request_count = 0
        self._success_count = 0
        self._failure_count = 0
        self._total_response_time = 0.0
        self._total_tokens = 0
        self._server_stats = defaultdict(lambda: {"requests": 0, "failures": 0, "total_time": 0.0})
        self._start_time = datetime.utcnow()

    async def record_request(
        self,
        model: str,
        server: str,
        response_time_ms: float,
        success: bool,
        tokens_used: int = 0,
        error: str = None
    ):
        """Record a request metric."""
        self._request_count += 1

        if success:
            self._success_count += 1
            self._total_response_time += response_time_ms
            self._total_tokens += tokens_used
        else:
            self._failure_count += 1

        self._server_stats[server]["requests"] += 1
        self._server_stats[server]["total_time"] += response_time_ms

        if not success:
            self._server_stats[server]["failures"] += 1

        # Store in Redis for distributed metrics
        await cache_service.increment("metrics:total_requests")
        if success:
            await cache_service.increment("metrics:success_requests")
        else:
            await cache_service.increment("metrics:failed_requests")

    async def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        avg_response_time = (
            self._total_response_time / self._request_count
            if self._request_count > 0
            else 0
        )

        cache_hit_rate = 0.0
        try:
            total = await cache_service.get("metrics:total_requests") or 0
            cache_hits = await cache_service.get("metrics:cache_hits") or 0
            if total > 0:
                cache_hit_rate = cache_hits / total
        except:
            pass

        # Calculate server load
        server_load = {}
        for server, stats in self._server_stats.items():
            avg_time = (
                stats["total_time"] / stats["requests"]
                if stats["requests"] > 0
                else 0
            )
            failure_rate = (
                stats["failures"] / stats["requests"]
                if stats["requests"] > 0
                else 0
            )
            server_load[server] = {
                "requests": stats["requests"],
                "avg_response_ms": round(avg_time, 2),
                "failure_rate": round(failure_rate, 3)
            }

        uptime = (datetime.utcnow() - self._start_time).total_seconds()

        return {
            "total_requests": self._request_count,
            "active_requests": self._request_count - (self._success_count + self._failure_count),
            "successful_requests": self._success_count,
            "failed_requests": self._failure_count,
            "avg_response_time_ms": round(avg_response_time, 2),
            "total_tokens": self._total_tokens,
            "cache_hit_rate": round(cache_hit_rate, 3),
            "server_load": server_load,
            "uptime_seconds": int(uptime)
        }

    async def reset(self):
        """Reset all metrics."""
        self._request_count = 0
        self._success_count = 0
        self._failure_count = 0
        self._total_response_time = 0.0
        self._total_tokens = 0
        self._server_stats.clear()


# Global instance
metrics_service = MetricsService()