"""Tests for asset upload and retrieval API."""

from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
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


@pytest.fixture()
def project_id(api_client: TestClient) -> str:
    """Create a project and return its id."""
    resp = api_client.post("/api/projects", data={"name": "Test Project"})
    assert resp.status_code == 201
    return resp.json()["id"]


@pytest.fixture()
def shot_id(db_engine, project_id: str) -> str:
    """Create a shot directly in the DB and return its id."""
    Session_ = sessionmaker(bind=db_engine)
    with Session_() as session:
        shot = Shot(
            project_id=project_id,
            order=1,
            start_time=0.0,
            end_time=5.0,
            duration=5.0,
        )
        session.add(shot)
        session.commit()
        session.refresh(shot)
        return shot.id


def _fake_image_bytes() -> bytes:
    """Return a minimal 1x1 red JPEG using Pillow."""
    try:
        from PIL import Image

        buf = io.BytesIO()
        img = Image.new("RGB", (1, 1), color=(255, 0, 0))
        img.save(buf, format="JPEG")
        return buf.getvalue()
    except Exception:
        return b"fake-image-data"


def test_upload_asset(api_client: TestClient, test_settings, project_id: str):
    """POST /assets/{project_id} should return 201, create DB record, and save file."""
    image_content = _fake_image_bytes()
    response = api_client.post(
        f"/api/assets/{project_id}",
        files={"file": ("photo.jpg", io.BytesIO(image_content), "image/jpeg")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["project_id"] == project_id
    assert body["name"] == "photo.jpg"
    assert body["storage_backend"] == "local"
    assert body["relative_path"].startswith(f"projects/{project_id}/assets/")
    assert body["mime_type"] == "image/jpeg"
    assert body["url"] == f"/api/assets/{project_id}/{body['id']}"
    assert body["thumb_url"] == f"/api/assets/{project_id}/{body['id']}/thumb"

    # Verify file actually exists on disk
    saved_path = test_settings.data_root / body["relative_path"]
    assert saved_path.exists()
    assert saved_path.read_bytes() == image_content


def test_list_assets(api_client: TestClient, project_id: str):
    """GET /assets/{project_id} should return all uploaded assets with url and thumb_url."""
    image_content = _fake_image_bytes()

    api_client.post(
        f"/api/assets/{project_id}",
        files={"file": ("alpha.jpg", io.BytesIO(image_content), "image/jpeg")},
    )
    api_client.post(
        f"/api/assets/{project_id}",
        files={"file": ("beta.jpg", io.BytesIO(image_content), "image/jpeg")},
    )

    response = api_client.get(f"/api/assets/{project_id}")
    assert response.status_code == 200
    assets = response.json()

    names = [a["name"] for a in assets]
    assert "alpha.jpg" in names
    assert "beta.jpg" in names

    for asset in assets:
        assert "url" in asset
        assert "thumb_url" in asset
        assert asset["url"].startswith(f"/api/assets/{project_id}/")
        assert asset["thumb_url"].startswith(f"/api/assets/{project_id}/")


def test_use_asset_for_shot(
    api_client: TestClient,
    db_engine,
    project_id: str,
    shot_id: str,
):
    """POST use-for-shot should create a new Attempt with the asset's image fields."""
    image_content = _fake_image_bytes()
    upload_resp = api_client.post(
        f"/api/assets/{project_id}",
        files={"file": ("frame.jpg", io.BytesIO(image_content), "image/jpeg")},
    )
    assert upload_resp.status_code == 201
    asset = upload_resp.json()

    use_resp = api_client.post(
        f"/api/assets/{project_id}/{asset['id']}/use-for-shot/{shot_id}",
    )
    assert use_resp.status_code == 201
    attempt = use_resp.json()

    assert attempt["shot_id"] == shot_id
    assert attempt["status"] == "Needs Input"
    assert attempt["image_storage_backend"] == "local"
    assert attempt["image_relative_path"] == asset["relative_path"]
    assert attempt["id"]

    # Verify the attempt exists in the DB
    Session_ = sessionmaker(bind=db_engine)
    with Session_() as session:
        db_attempt = session.get(Attempt, attempt["id"])
        assert db_attempt is not None
        assert db_attempt.shot_id == shot_id
        assert db_attempt.image_relative_path == asset["relative_path"]


def test_use_asset_for_shot_creates_new_attempt_not_overwrite(
    api_client: TestClient,
    db_engine,
    project_id: str,
    shot_id: str,
):
    """Calling use-for-shot twice for the same shot should create 2 separate attempts."""
    image_content = _fake_image_bytes()
    upload_resp = api_client.post(
        f"/api/assets/{project_id}",
        files={"file": ("frame.jpg", io.BytesIO(image_content), "image/jpeg")},
    )
    assert upload_resp.status_code == 201
    asset = upload_resp.json()

    resp1 = api_client.post(
        f"/api/assets/{project_id}/{asset['id']}/use-for-shot/{shot_id}",
    )
    assert resp1.status_code == 201
    attempt1_id = resp1.json()["id"]

    resp2 = api_client.post(
        f"/api/assets/{project_id}/{asset['id']}/use-for-shot/{shot_id}",
    )
    assert resp2.status_code == 201
    attempt2_id = resp2.json()["id"]

    # The two attempts must be different records
    assert attempt1_id != attempt2_id

    # Verify both exist in the DB
    Session_ = sessionmaker(bind=db_engine)
    with Session_() as session:
        attempts = list(
            session.scalars(
                select(Attempt).where(Attempt.shot_id == shot_id)
            ).all()
        )
        assert len(attempts) == 2
