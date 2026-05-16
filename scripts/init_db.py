"""Initialize database tables."""
import asyncio
import sys
sys.path.insert(0, '/home/asim/asim/RAG')

from app.models.database import db_manager
from app.logging_config import log


async def init_database():
    """Initialize database tables."""
    log.info("Initializing database...")

    try:
        await db_manager.init()
        log.info("Database initialized successfully")
    except Exception as e:
        log.error(f"Failed to initialize database: {e}")
        raise
    finally:
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(init_database())