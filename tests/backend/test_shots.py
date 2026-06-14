"""Tests for shot and attempt API routes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from eumpa_studio.config import Settings
from eumpa_studio.db.base import Base
from eumpa_studio.db.session import get_session
from eumpa_studio.domain.models import Attempt, Project, Shot
from eumpa_studio.server.app import app
from eumpa_studio.server.deps import get_settings_dep


@pytest.fixture()
def test_settings(tmp_path):
    return Settings(
        data_root=tmp_path / "data",
        database_url="sqlite:///:memory:",
    )


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
def db_session(db_engine):
    Session_ = sessionmaker(bind=db_engine)
    with Session_() as session:
        yield session


@pytest.fixture()
def api_client(test_settings, db_engine):
    Session_ = sessionmaker(bind=db_engine)

    def override_get_db():
        with Session_() as session:
            yield session

    def override_get_settings():
        return test_settings

    app.dependency_overrides[get_session] = override_get_db
    app.dependency_overrides[get_settings_dep] = override_get_settings
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def _create_attempt(session: Session) -> Attempt:
    project = Project(name="Prompt Project")
    session.add(project)
    session.flush()

    shot = Shot(
        project_id=project.id,
        order=1,
        start_time=0,
        end_time=4,
        duration=4,
        lyrics_text="first line",
    )
    session.add(shot)
    session.flush()

    attempt = Attempt(
        shot_id=shot.id,
        prompt_ko="old ko",
        prompt_en="old en",
        review_note="old note",
    )
    session.add(attempt)
    session.commit()
    session.refresh(attempt)
    return attempt


def test_patch_attempt_updates_prompt_fields(
    api_client: TestClient, db_session: Session
):
    """PATCH /api/shots/{shot_id}/attempts/{attempt_id} updates editable fields."""
    attempt = _create_attempt(db_session)

    response = api_client.patch(
        f"/api/shots/{attempt.shot_id}/attempts/{attempt.id}",
        json={
            "prompt_ko": "updated ko",
            "prompt_en": "updated en",
            "review_note": "updated note",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == attempt.id
    assert body["shot_id"] == attempt.shot_id
    assert body["prompt_ko"] == "updated ko"
    assert body["prompt_en"] == "updated en"
    assert body["review_note"] == "updated note"
    assert body["status"] == attempt.status
    assert body["created_at"]


def test_patch_attempt_rejects_wrong_shot_id(
    api_client: TestClient, db_session: Session
):
    """The nested shot id must match the attempt's real shot id."""
    attempt = _create_attempt(db_session)

    response = api_client.patch(
        f"/api/shots/not-the-shot/attempts/{attempt.id}",
        json={"prompt_en": "should not save"},
    )

    assert response.status_code == 404
