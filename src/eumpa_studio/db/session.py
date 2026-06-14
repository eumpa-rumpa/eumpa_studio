"""Database session factory for eumpa_studio."""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

_DATABASE_URL = os.environ.get(
    "DATABASE_URL", "sqlite:///eumpa_studio.db"
)

engine = create_engine(
    _DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal: sessionmaker[Session] = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_session() -> Session:
    """Create and return a new database session.

    Caller is responsible for closing it (use as context manager or call .close()).
    """
    return SessionLocal()
