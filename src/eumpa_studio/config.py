"""Application settings for eumpa_studio."""

import os
from functools import lru_cache
from pathlib import Path


class Settings:
    """Application configuration loaded from environment variables."""

    def __init__(self) -> None:
        self.comfyui_url: str = os.environ.get(
            "COMFYUI_URL", "http://localhost:8188"
        )
        self.data_root: Path = Path(
            os.environ.get("EUMPA_DATA_ROOT", "data")
        )
        self.output_path: Path = Path(
            os.environ.get("EUMPA_OUTPUT_PATH", "data/output")
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()


def get_settings_dep() -> Settings:
    """FastAPI dependency that returns application settings."""
    return get_settings()
