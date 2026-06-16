"""Tests for project creation and retrieval API."""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from eumpa_studio.config import Settings
from eumpa_studio.db.base import Base
from eumpa_studio.db.session import get_session
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
        with Session_() as s:
            yield s

    def override_get_settings():
        return test_settings

    app.dependency_overrides[get_session] = override_get_db
    app.dependency_overrides[get_settings_dep] = override_get_settings
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_create_project_minimal(api_client: TestClient, test_settings):
    """POST with just a name (no files) should return 201 and persist the project."""
    response = api_client.post("/api/projects", data={"name": "My Project"})

    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["name"] == "My Project"
    assert body["audio_storage_backend"] is None
    assert body["audio_relative_path"] is None
    assert body["created_at"]
    assert body["updated_at"]


def test_create_project_with_audio(api_client: TestClient, test_settings):
    """POST with name + audio file should save the file and record relative path."""
    audio_content = b"fake audio data"
    response = api_client.post(
        "/api/projects",
        data={"name": "Audio Project"},
        files={"audio": ("track.mp3", io.BytesIO(audio_content), "audio/mpeg")},
    )

    assert response.status_code == 201
    body = response.json()
    project_id = body["id"]

    assert body["audio_storage_backend"] == "local"
    expected_rel = f"projects/{project_id}/inputs/track.mp3"
    assert body["audio_relative_path"] == expected_rel

    # Verify the file actually exists on disk
    saved_path = test_settings.data_root / expected_rel
    assert saved_path.exists()
    assert saved_path.read_bytes() == audio_content


def test_get_project_audio_serves_uploaded_audio(api_client: TestClient):
    """GET /api/projects/{id}/audio should serve the stored project audio file."""
    audio_content = b"fake audio data"
    create_response = api_client.post(
        "/api/projects",
        data={"name": "Audio Preview Project"},
        files={"audio": ("track.mp3", io.BytesIO(audio_content), "audio/mpeg")},
    )
    assert create_response.status_code == 201
    project_id = create_response.json()["id"]

    response = api_client.get(f"/api/projects/{project_id}/audio")

    assert response.status_code == 200
    assert response.content == audio_content
    assert response.headers["content-type"].startswith("audio/")


def test_get_project_audio_without_audio_returns_404(api_client: TestClient):
    """GET /api/projects/{id}/audio should be explicit when a project has no audio."""
    create_response = api_client.post("/api/projects", data={"name": "Silent Project"})
    assert create_response.status_code == 201
    project_id = create_response.json()["id"]

    response = api_client.get(f"/api/projects/{project_id}/audio")

    assert response.status_code == 404
    assert response.json()["detail"] == "Project audio not found"


def test_list_projects(api_client: TestClient):
    """GET /api/projects should return all created projects."""
    api_client.post("/api/projects", data={"name": "Project Alpha"})
    api_client.post("/api/projects", data={"name": "Project Beta"})

    response = api_client.get("/api/projects")

    assert response.status_code == 200
    projects = response.json()
    names = [p["name"] for p in projects]
    assert "Project Alpha" in names
    assert "Project Beta" in names


def test_get_project(api_client: TestClient):
    """GET /api/projects/{id} should return the full project detail."""
    create_response = api_client.post(
        "/api/projects",
        data={"name": "Detail Project", "lyrics_text": "verse one"},
    )
    assert create_response.status_code == 201
    project_id = create_response.json()["id"]

    response = api_client.get(f"/api/projects/{project_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == project_id
    assert body["name"] == "Detail Project"
    assert body["lyrics_text"] == "verse one"


def test_get_project_not_found(api_client: TestClient):
    """GET /api/projects/{id} with unknown id should return 404."""
    response = api_client.get("/api/projects/nonexistent-id")
    assert response.status_code == 404
