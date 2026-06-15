"""Database session factory for eumpa_studio."""

import os
from typing import Generator

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


def get_session() -> Generator[Session, None, None]:
    """Yield a database session and ensure it is closed afterwards.

    Use as a FastAPI dependency or context manager.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
