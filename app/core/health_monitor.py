"""Health monitoring for Ollama servers."""
import asyncio
from typing import Dict, List
from datetime import datetime

from app.config import settings
from app.logging_config import log
from app.core.ollama_cluster import ollama_cluster


class HealthMonitor:
    """Monitors health of Ollama servers."""

    def __init__(self):
        self.is_running = False
        self.task: asyncio.Task = None

    async def start(self):
        """Start health monitoring."""
        if self.is_running:
            log.warning("Health monitor already running")
            return

        self.is_running = True
        self.task = asyncio.create_task(self._monitor_loop())
        log.info("Health monitor started")

    async def stop(self):
        """Stop health monitoring."""
        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        log.info("Health monitor stopped")

    async def _monitor_loop(self):
        """Main monitoring loop."""
        while self.is_running:
            try:
                await self._check_servers()
                await asyncio.sleep(settings.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error(f"Health check error: {e}")
                await asyncio.sleep(5)

    async def _check_servers(self):
        """Check all servers."""
        await ollama_cluster.check_all_servers()

        # Log unhealthy servers
        unhealthy = [
            (url, server) for url, server in ollama_cluster.servers.items()
            if not server.is_healthy
        ]

        if unhealthy:
            log.warning(f"Unhealthy servers: {unhealthy}")

    async def get_health_status(self) -> Dict:
        """Get current health status of all servers."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "servers": [
                {
                    "url": url,
                    "name": server.name,
                    "healthy": server.is_healthy,
                    "response_time_ms": server.response_time_ms,
                    "consecutive_failures": server.consecutive_failures,
                    "consecutive_successes": server.consecutive_successes,
                    "last_check": server.last_check.isoformat() if server.last_check else None,
                    "loaded_models": server.loaded_models
                }
                for url, server in ollama_cluster.servers.items()
            ]
        }

    async def force_recheck(self):
        """Force a health check of all servers."""
        await ollama_cluster.check_all_servers()
        return await self.get_health_status()


# Global health monitor instance
health_monitor = HealthMonitor()