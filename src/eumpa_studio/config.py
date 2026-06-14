"""Application configuration for eumpa_studio."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    data_root: Path = Path("data")
    comfyui_url: str = "http://localhost:8188"
    codex_cli_path: str = "codex"
    alignment_command: str = "align"
    output_path: Path = Path("data/output")
    cache_path: Path = Path("data/cache")
    database_url: str = "sqlite:///eumpa_studio.db"

    model_config = SettingsConfigDict(
        env_prefix="EUMPA_",
        env_file=".env",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings singleton."""
    return Settings()
