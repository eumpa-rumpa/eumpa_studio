"""Tests for studio-wide settings routes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from eumpa_studio.db.base import Base
from eumpa_studio.db.session import get_session
from eumpa_studio.execution.codex_prompt import DEFAULT_SYSTEM_PROMPT
from eumpa_studio.server.app import app


@pytest.fixture()
def db_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def api_client(db_engine):
    Session_ = sessionmaker(bind=db_engine)

    def override_get_db():
        with Session_() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_prompt_system_default_returns_builtin_default(api_client: TestClient):
    response = api_client.get("/api/settings/prompt-system-default")

    assert response.status_code == 200
    body = response.json()
    assert body["system_prompt"] == DEFAULT_SYSTEM_PROMPT
    assert body["is_custom"] is False
    assert body["updated_at"] is None


def test_prompt_system_default_can_be_saved(api_client: TestClient):
    response = api_client.patch(
        "/api/settings/prompt-system-default",
        json={"system_prompt": "Custom studio-wide LTX instruction"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["system_prompt"] == "Custom studio-wide LTX instruction"
    assert body["is_custom"] is True
    assert body["updated_at"] is not None

    get_response = api_client.get("/api/settings/prompt-system-default")

    assert get_response.status_code == 200
    assert get_response.json()["system_prompt"] == "Custom studio-wide LTX instruction"
