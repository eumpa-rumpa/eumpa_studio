"""Application settings for eumpa_studio."""

import os
from functools import lru_cache


class Settings:
    """Application configuration loaded from environment variables."""

    def __init__(self) -> None:
        self.comfyui_url: str = os.environ.get(
            "COMFYUI_URL", "http://localhost:8188"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()


def get_settings_dep() -> Settings:
    """FastAPI dependency that returns application settings."""
    return get_settings()
