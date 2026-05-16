"""Application configuration using environment variables."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Dict, List, Optional
import json
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    app_name: str = Field(default="RAG-Inference-Platform", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    debug: bool = Field(default=False, alias="DEBUG")

    # API
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_prefix: str = Field(default="/api/v1", alias="API_PREFIX")

    # CORS
    cors_origins: str = Field(default="*", alias="CORS_ORIGINS")

    # Security
    secret_key: str = Field(default="secret-key", alias="SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expiration_minutes: int = Field(default=1440, alias="JWT_EXPIRATION_MINUTES")

    # Ollama Cluster
    ollama_servers: str = Field(default="http://localhost:11434", alias="OLLAMA_SERVERS")
    model_server_map: str = Field(default="{}", alias="MODEL_SERVER_MAP")
    default_model: str = Field(default="llama3.2", alias="DEFAULT_MODEL")
    embedding_model: str = Field(default="nomic-embed-text", alias="EMBEDDING_MODEL")
    fallback_servers: str = Field(default="", alias="FALLBACK_SERVERS")
    load_balancing_strategy: str = Field(default="weighted", alias="LOAD_BALANCING_STRATEGY")

    # Health Monitoring
    health_check_interval: int = Field(default=30, alias="HEALTH_CHECK_INTERVAL")
    health_check_timeout: int = Field(default=5, alias="HEALTH_CHECK_TIMEOUT")
    unhealthy_threshold: int = Field(default=3, alias="UNHEALTHY_THRESHOLD")
    recovery_threshold: int = Field(default=2, alias="RECOVERY_THRESHOLD")

    # Qdrant
    qdrant_host: str = Field(default="localhost", alias="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, alias="QDRANT_PORT")
    qdrant_grpc_port: int = Field(default=6334, alias="QDRANT_GRPC_PORT")
    qdrant_collection: str = Field(default="rag_memories", alias="QDRANT_COLLECTION")
    qdrant_vector_size: int = Field(default=768, alias="QDRANT_VECTOR_SIZE")

    # Redis
    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")
    redis_password: str = Field(default="", alias="REDIS_PASSWORD")
    redis_cache_ttl: int = Field(default=3600, alias="REDIS_CACHE_TTL")

    # PostgreSQL
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_user: str = Field(default="rag_user", alias="POSTGRES_USER")
    postgres_password: str = Field(default="password", alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="rag_platform", alias="POSTGRES_DB")
    database_url: str = Field(default="", alias="DATABASE_URL")

    # RAG
    chunk_size: int = Field(default=500, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=50, alias="CHUNK_OVERLAP")
    top_k_memories: int = Field(default=5, alias="TOP_K_MEMORIES")
    max_context_length: int = Field(default=4096, alias="MAX_CONTEXT_LENGTH")
    similarity_threshold: float = Field(default=0.7, alias="SIMILARITY_THRESHOLD")

    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    rate_limit_requests: int = Field(default=100, alias="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, alias="RATE_LIMIT_WINDOW")

    # Retry & Timeout
    request_timeout: int = Field(default=120, alias="REQUEST_TIMEOUT")
    max_retries: int = Field(default=3, alias="MAX_RETRIES")
    retry_delay: int = Field(default=1, alias="RETRY_DELAY")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_format: str = Field(default="json", alias="LOG_FORMAT")
    log_file: str = Field(default="logs/app.log", alias="LOG_FILE")

    # Metrics
    enable_metrics: bool = Field(default=True, alias="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, alias="METRICS_PORT")

    @field_validator("model_server_map", mode="before")
    @classmethod
    def parse_model_map(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except:
                return {}
        return v

    def get_ollama_servers(self) -> List[str]:
        """Get list of Ollama servers."""
        return [s.strip() for s in self.ollama_servers.split(",") if s.strip()]

    def get_fallback_servers(self) -> List[str]:
        """Get list of fallback servers."""
        if not self.fallback_servers:
            return self.get_ollama_servers()
        return [s.strip() for s in self.fallback_servers.split(",") if s.strip()]

    def get_model_server_mapping(self) -> Dict[str, str]:
        """Get model to server mapping."""
        if isinstance(self.model_server_map, str):
            try:
                return json.loads(self.model_server_map)
            except:
                return {}
        return self.model_server_map


settings = Settings()

# Ensure DATABASE_URL is set if not provided
if not settings.database_url:
    settings.database_url = f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"