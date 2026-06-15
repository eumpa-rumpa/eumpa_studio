"""Tests for shot production API routes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from eumpa_studio.config import Settings
from eumpa_studio.db.base import Base
from eumpa_studio.db.session import get_session
from eumpa_studio.domain.models import Attempt, Project, Shot
from eumpa_studio.domain.statuses import AttemptStatus, ShotStatus
from eumpa_studio.server.app import app
from eumpa_studio.server.deps import get_settings_dep


@pytest.fixture()
def test_settings(tmp_path):
    return Settings(
        data_root=tmp_path / "data",
        database_url="sqlite:///:memory:",
    )


@pytest.fixture()
def db_engine(test_settings):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


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


@pytest.fixture()
def db_session(db_engine):
    Session_ = sessionmaker(bind=db_engine)
    with Session_() as session:
        yield session


def test_list_shot_attempts_returns_attempts_for_shot(
    api_client: TestClient,
    db_session,
):
    project = Project(name="Attempt Review Project")
    db_session.add(project)
    db_session.commit()

    shot = Shot(
        project_id=project.id,
        order=0,
        start_time=1.0,
        end_time=3.5,
        duration=2.5,
        lyrics_text="line one",
        status=ShotStatus.NEEDS_REVIEW.value,
    )
    db_session.add(shot)
    db_session.commit()

    first_attempt = Attempt(
        shot_id=shot.id,
        status=AttemptStatus.NEEDS_REVIEW.value,
        prompt_ko="첫 번째 한국어 프롬프트",
        prompt_en="First English prompt",
        review_note="needs stronger composition",
    )
    second_attempt = Attempt(
        shot_id=shot.id,
        status=AttemptStatus.REDO.value,
        prompt_ko="두 번째 한국어 프롬프트",
        prompt_en="Second English prompt",
    )
    other_shot = Shot(
        project_id=project.id,
        order=1,
        start_time=3.5,
        end_time=5.0,
        duration=1.5,
    )
    db_session.add_all([first_attempt, second_attempt, other_shot])
    db_session.commit()
    other_attempt = Attempt(shot_id=other_shot.id, status=AttemptStatus.READY.value)
    db_session.add(other_attempt)
    db_session.commit()

    response = api_client.get(f"/api/shots/{shot.id}/attempts")

    assert response.status_code == 200
    attempts = response.json()
    assert {attempt["id"] for attempt in attempts} == {first_attempt.id, second_attempt.id}

    first_body = next(attempt for attempt in attempts if attempt["id"] == first_attempt.id)
    assert first_body["status"] == AttemptStatus.NEEDS_REVIEW.value
    assert first_body["prompt_ko"] == "첫 번째 한국어 프롬프트"
    assert first_body["prompt_en"] == "First English prompt"
    assert first_body["review_note"] == "needs stronger composition"
    assert first_body["created_at"]


def test_update_attempt_review_note(api_client: TestClient, db_session):
    project = Project(name="Review Note Project")
    db_session.add(project)
    db_session.commit()

    shot = Shot(
        project_id=project.id,
        order=0,
        start_time=0.0,
        end_time=2.0,
        duration=2.0,
    )
    db_session.add(shot)
    db_session.commit()

    attempt = Attempt(
        shot_id=shot.id,
        status=AttemptStatus.NEEDS_REVIEW.value,
        prompt_en="Review this frame",
    )
    db_session.add(attempt)
    db_session.commit()

    response = api_client.patch(
        f"/api/shots/{shot.id}/attempts/{attempt.id}",
        json={"review_note": "tighten the close-up before approval"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == attempt.id
    assert body["review_note"] == "tighten the close-up before approval"
