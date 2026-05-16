"""Logging configuration for the application."""
import sys
import json
from pathlib import Path
from loguru import logger
from datetime import datetime

from app.config import settings


class JSONFormatter:
    """JSON formatter for structured logging."""

    def __call__(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record["level"].name,
            "message": record["message"],
            "module": record["name"],
            "function": record["function"],
            "line": record["line"]
        }

        if record["exception"]:
            log_data["exception"] = str(record["exception"])

        # Add extra fields
        for key, value in record["extra"].items():
            log_data[key] = value

        return json.dumps(log_data)


def setup_logging():
    """Configure loguru with custom settings."""
    # Remove default handler
    logger.remove()

    # Create logs directory
    log_path = Path("logs")
    log_path.mkdir(exist_ok=True)

    # Console format
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    # Add console handler
    logger.add(
        sys.stdout,
        format=console_format,
        level=settings.log_level,
        colorize=True,
        backtrace=True,
        diagnose=True
    )

    # Add file handler with rotation
    logger.add(
        settings.log_file,
        format=console_format,
        level=settings.log_level,
        rotation="50 MB",
        retention="7 days",
        compression="zip",
        enqueue=True
    )

    # Add error-specific log file
    logger.add(
        "logs/error.log",
        format=console_format,
        level="ERROR",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        enqueue=True
    )

    return logger


log = setup_logging()


def get_logger(name: str):
    """Get a logger instance with the given name."""
    return logger.bind(name=name)