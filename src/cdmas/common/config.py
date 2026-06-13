"""Centralized runtime configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All CDMAS_* environment variables (see .env.example)."""

    model_config = SettingsConfigDict(env_prefix="CDMAS_", env_file=".env", extra="ignore")

    # Message bus
    kafka_bootstrap: str = "localhost:9092"
    kafka_client_id: str = "cdmas"
    # Simulator
    sim_host: str = "0.0.0.0"
    sim_port: int = 8000
    sim_base_url: str = "http://localhost:8000"
    sim_api_token: str = "changeme"
    sim_speed: float = 1.0
    sim_tick_ms: int = 10
    # Live dashboard server (single-process MAS demo)
    live_port: int | None = None  # falls back to sim_port
    live_cors_origins: str = "*"  # comma-separated allowed origins ("*" = any, dev only)
    # Persistence
    db_url: str = "postgresql+asyncpg://cdmas:cdmas@localhost:5432/cdmas"
    # Logging
    log_level: str = "INFO"
    log_json: bool = True
    # Agent identity (set per container)
    agent_id: str | None = None
    agent_segment: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
