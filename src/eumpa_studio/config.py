"""Application configuration for eumpa_studio."""

from functools import lru_cache
import os
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


def database_url_from_env() -> str:
    """Return the configured database URL.

    Prefer the app-scoped environment variable. Keep ``DATABASE_URL`` as a
    compatibility fallback for hosted environments and older local scripts.
    ``Settings`` is used last so values from .env are honored in cloned repos.
    """
    return (
        os.environ.get("EUMPA_DATABASE_URL")
        or os.environ.get("DATABASE_URL")
        or str(Settings().database_url)
    )


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings singleton."""
    return Settings()


def get_settings_dep() -> Settings:
    """FastAPI dependency that returns the application settings singleton."""
    return get_settings()
