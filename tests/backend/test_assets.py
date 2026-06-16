"""Tests for project asset upload and shot attempt creation routes."""

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
from eumpa_studio.domain.models import Project, Shot
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


def test_upload_asset_and_use_for_shot(api_client: TestClient, db_session, test_settings):
    project = Project(name="Asset Upload Project")
    db_session.add(project)
    db_session.commit()

    shot = Shot(
        project_id=project.id,
        order=0,
        start_time=0,
        end_time=5,
        duration=5,
    )
    db_session.add(shot)
    db_session.commit()

    response = api_client.post(
        f"/api/assets/{project.id}",
        files={"file": ("reference.png", io.BytesIO(b"fake image"), "image/png")},
    )

    assert response.status_code == 201
    asset = response.json()
    assert asset["name"] == "reference.png"
    assert asset["relative_path"].endswith("_reference.png")
    assert (test_settings.data_root / asset["relative_path"]).read_bytes() == b"fake image"

    attempt_response = api_client.post(
        f"/api/assets/{project.id}/{asset['id']}/use-for-shot/{shot.id}",
    )

    assert attempt_response.status_code == 201
    attempt = attempt_response.json()
    assert attempt["shot_id"] == shot.id
    assert attempt["image_relative_path"] == asset["relative_path"]
