"""Tests for attempt review status and video-url endpoints."""

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from eumpa_studio.config import Settings, get_settings_dep
from eumpa_studio.db.base import Base
from eumpa_studio.db.session import get_session
from eumpa_studio.domain.models import Attempt, Project, Shot
from eumpa_studio.domain.statuses import AttemptStatus
from eumpa_studio.server.app import app


@pytest.fixture()
def session_factory():
    """In-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session_ = sessionmaker(bind=engine)
    yield Session_
    Base.metadata.drop_all(engine)
    engine.dispose()


def _fake_settings() -> Settings:
    settings = Settings.__new__(Settings)
    settings.comfyui_url = "http://comfyui.test"
    return settings


@pytest.fixture()
def api_client(session_factory):
    def override_get_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_settings_dep] = _fake_settings
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def _create_shot_and_attempt(session_factory, *, output_metadata: dict | None = None) -> tuple[str, str]:
    """Helper to create a project, shot, and attempt. Returns (shot_id, attempt_id)."""
    with session_factory() as session:
        project = Project(
            name="Test Project",
            audio_storage_backend="local",
            audio_relative_path="audio/song.wav",
        )
        session.add(project)
        session.flush()

        shot = Shot(
            project_id=project.id,
            order=1,
            start_time=0.0,
            end_time=5.0,
            duration=5.0,
        )
        session.add(shot)
        session.flush()

        attempt = Attempt(
            shot_id=shot.id,
            status=AttemptStatus.NEEDS_REVIEW.value,
            output_metadata=json.dumps(output_metadata) if output_metadata is not None else None,
        )
        session.add(attempt)
        session.commit()
        session.refresh(attempt)
        return shot.id, attempt.id


def test_review_selected_updates_shot_active_attempt(api_client, session_factory):
    shot_id, attempt_id = _create_shot_and_attempt(session_factory)

    response = api_client.post(
        f"/api/shots/{shot_id}/attempts/{attempt_id}/review",
        json={"status": "Selected"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Selected"
    assert data["id"] == attempt_id

    # Verify shot.active_attempt_id is updated
    with session_factory() as session:
        shot = session.get(Shot, shot_id)
        assert shot is not None
        assert shot.active_attempt_id == attempt_id


def test_review_redo_does_not_change_active_attempt(api_client, session_factory):
    shot_id, attempt_id = _create_shot_and_attempt(session_factory)

    # Confirm shot has no active_attempt_id initially
    with session_factory() as session:
        shot = session.get(Shot, shot_id)
        assert shot is not None
        original_active_id = shot.active_attempt_id

    response = api_client.post(
        f"/api/shots/{shot_id}/attempts/{attempt_id}/review",
        json={"status": "Redo"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Redo"

    # active_attempt_id should remain unchanged
    with session_factory() as session:
        shot = session.get(Shot, shot_id)
        assert shot is not None
        assert shot.active_attempt_id == original_active_id


def test_review_saves_review_note(api_client, session_factory):
    shot_id, attempt_id = _create_shot_and_attempt(session_factory)

    response = api_client.post(
        f"/api/shots/{shot_id}/attempts/{attempt_id}/review",
        json={"status": "Rejected", "review_note": "Colors are off"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Rejected"
    assert data["review_note"] == "Colors are off"

    # Verify persisted in DB
    with session_factory() as session:
        attempt = session.get(Attempt, attempt_id)
        assert attempt is not None
        assert attempt.review_note == "Colors are off"


def test_video_url_returns_comfyui_view_url(api_client, session_factory):
    output_meta = {
        "filename": "render_0001.mp4",
        "subfolder": "final",
        "type": "output",
        "server_id": "http://comfyui.test",
    }
    shot_id, attempt_id = _create_shot_and_attempt(session_factory, output_metadata=output_meta)

    response = api_client.get(f"/api/shots/{shot_id}/attempts/{attempt_id}/video-url")

    assert response.status_code == 200
    data = response.json()
    assert data["video_url"] == (
        "http://comfyui.test/view?filename=render_0001.mp4&subfolder=final&type=output"
    )


def test_video_url_404_when_no_output_metadata(api_client, session_factory):
    shot_id, attempt_id = _create_shot_and_attempt(session_factory, output_metadata=None)

    response = api_client.get(f"/api/shots/{shot_id}/attempts/{attempt_id}/video-url")

    assert response.status_code == 404
