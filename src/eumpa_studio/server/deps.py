"""FastAPI dependency functions for eumpa_studio."""

from typing import Generator

from sqlalchemy.orm import Session

from eumpa_studio.config import Settings, get_settings
from eumpa_studio.db.session import get_session


def get_settings_dep() -> Settings:
    """FastAPI dependency that returns the application settings singleton."""
    return get_settings()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    yield from get_session()
