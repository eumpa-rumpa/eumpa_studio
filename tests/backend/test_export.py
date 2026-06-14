"""Tests for export selected clips and metadata (EPR-19)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from eumpa_studio.config import Settings, get_settings_dep
from eumpa_studio.db.base import Base
from eumpa_studio.db.session import get_session
from eumpa_studio.domain.models import Attempt, Project, Shot
from eumpa_studio.domain.statuses import AttemptStatus, ShotStatus
from eumpa_studio.export.selected import collect_selected_attempts, export_project
from eumpa_studio.server.app import app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def session_factory(tmp_path):
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


def _make_settings(tmp_path: Path) -> Settings:
    s = Settings.__new__(Settings)
    s.comfyui_url = "http://comfyui.test"
    s.data_root = tmp_path / "data"
    s.output_path = tmp_path / "output"
    s.data_root.mkdir(parents=True, exist_ok=True)
    s.output_path.mkdir(parents=True, exist_ok=True)
    return s


@pytest.fixture()
def api_client(session_factory, tmp_path):
    test_settings = _make_settings(tmp_path)

    def override_get_session():
        with session_factory() as session:
            yield session

    def override_get_settings():
        return test_settings

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_settings_dep] = override_get_settings
    with TestClient(app) as client:
        yield client, test_settings
    app.dependency_overrides.clear()


def _create_project(session_factory) -> str:
    """Create a minimal project and return its id."""
    with session_factory() as session:
        project = Project(
            name="Test Project",
            audio_storage_backend="local",
            audio_relative_path="audio/song.wav",
        )
        session.add(project)
        session.commit()
        session.refresh(project)
        return project.id


def _create_shot(session_factory, project_id: str, order: int, lyrics: str = "") -> str:
    """Create a shot and return its id."""
    with session_factory() as session:
        shot = Shot(
            project_id=project_id,
            order=order,
            start_time=float(order),
            end_time=float(order) + 1.0,
            duration=1.0,
            speaker="vocalist",
            lyrics_text=lyrics or f"Line {order}",
        )
        session.add(shot)
        session.commit()
        session.refresh(shot)
        return shot.id


def _create_attempt(
    session_factory,
    shot_id: str,
    status: str,
    output_metadata: dict | None = None,
    prompt_ko: str | None = None,
    prompt_en: str | None = None,
    seed: int | None = None,
) -> str:
    """Create an attempt and return its id."""
    with session_factory() as session:
        attempt = Attempt(
            shot_id=shot_id,
            status=status,
            output_metadata=json.dumps(output_metadata) if output_metadata is not None else None,
            prompt_ko=prompt_ko,
            prompt_en=prompt_en,
            seed=seed,
            workflow_template_id=None,
            execution_mode_id=None,
            param_overrides=None,
            workflow_snapshot=None,
        )
        session.add(attempt)
        session.commit()
        session.refresh(attempt)
        return attempt.id


def _select_attempt(session_factory, shot_id: str, attempt_id: str) -> None:
    """Mark an attempt as SELECTED and set it as the shot's active attempt."""
    with session_factory() as session:
        attempt = session.get(Attempt, attempt_id)
        attempt.status = AttemptStatus.SELECTED.value
        shot = session.get(Shot, shot_id)
        shot.active_attempt_id = attempt_id
        shot.status = ShotStatus.SELECTED.value
        session.commit()


# ---------------------------------------------------------------------------
# Test 1: empty project — no selected shots
# ---------------------------------------------------------------------------


def test_export_empty_project(session_factory, tmp_path):
    project_id = _create_project(session_factory)
    data_root = tmp_path / "data"
    data_root.mkdir(parents=True, exist_ok=True)
    export_root = tmp_path / "output"
    export_root.mkdir(parents=True, exist_ok=True)

    with session_factory() as session:
        result = export_project(session, project_id, data_root, export_root)

    assert result["clip_count"] == 0
    export_dir = Path(result["export_dir"])
    assert export_dir.exists()

    shot_list_path = Path(result["shot_list"])
    snapshots_path = Path(result["snapshots"])
    assert shot_list_path.exists()
    assert snapshots_path.exists()

    shot_list = json.loads(shot_list_path.read_text())
    snapshots = json.loads(snapshots_path.read_text())
    assert shot_list == []
    assert snapshots == []


# ---------------------------------------------------------------------------
# Test 2: 3 shots, 2 with selected attempts — verify order and fields
# ---------------------------------------------------------------------------


def test_export_selected_shots_in_order(session_factory, tmp_path):
    project_id = _create_project(session_factory)

    shot_id_1 = _create_shot(session_factory, project_id, order=1, lyrics="First line")
    shot_id_2 = _create_shot(session_factory, project_id, order=2, lyrics="Second line")
    shot_id_3 = _create_shot(session_factory, project_id, order=3, lyrics="Third line")

    attempt_id_1 = _create_attempt(
        session_factory, shot_id_1, AttemptStatus.NEEDS_REVIEW.value,
        prompt_en="shot one"
    )
    attempt_id_3 = _create_attempt(
        session_factory, shot_id_3, AttemptStatus.NEEDS_REVIEW.value,
        prompt_en="shot three"
    )
    # shot 2 has no selected attempt
    _create_attempt(session_factory, shot_id_2, AttemptStatus.REDO.value)

    _select_attempt(session_factory, shot_id_1, attempt_id_1)
    _select_attempt(session_factory, shot_id_3, attempt_id_3)

    data_root = tmp_path / "data"
    data_root.mkdir(parents=True, exist_ok=True)
    export_root = tmp_path / "output"
    export_root.mkdir(parents=True, exist_ok=True)

    with session_factory() as session:
        result = export_project(session, project_id, data_root, export_root)

    # 2 selected shots, 0 clips copied (no actual files on disk)
    assert result["clip_count"] == 0

    shot_list = json.loads(Path(result["shot_list"]).read_text())
    assert len(shot_list) == 2

    # Verify ordering: shot 1 comes before shot 3
    assert shot_list[0]["order"] == 1
    assert shot_list[1]["order"] == 3

    # Verify required fields
    first = shot_list[0]
    assert first["shot_id"] == shot_id_1
    assert first["attempt_id"] == attempt_id_1
    assert first["lyrics_text"] == "First line"
    assert first["start_time"] == 1.0
    assert first["end_time"] == 2.0
    assert first["speaker"] == "vocalist"
    assert first["prompt_en"] == "shot one"

    second = shot_list[1]
    assert second["shot_id"] == shot_id_3
    assert second["attempt_id"] == attempt_id_3
    assert second["lyrics_text"] == "Third line"


# ---------------------------------------------------------------------------
# Test 3: attempt_snapshots.json contains prompt/seed/workflow fields
# ---------------------------------------------------------------------------


def test_export_attempt_snapshots(session_factory, tmp_path):
    project_id = _create_project(session_factory)
    shot_id = _create_shot(session_factory, project_id, order=1)
    attempt_id = _create_attempt(
        session_factory,
        shot_id,
        AttemptStatus.NEEDS_REVIEW.value,
        output_metadata={"filename": "clip.mp4", "subfolder": "videos", "type": "output"},
        prompt_ko="한국어 프롬프트",
        prompt_en="English prompt",
        seed=42,
    )
    _select_attempt(session_factory, shot_id, attempt_id)

    # Also pre-populate workflow_snapshot and param_overrides directly
    with session_factory() as session:
        attempt = session.get(Attempt, attempt_id)
        attempt.workflow_snapshot = json.dumps({"node": "data"})
        attempt.param_overrides = json.dumps({"steps": 30})
        session.commit()

    data_root = tmp_path / "data"
    data_root.mkdir(parents=True, exist_ok=True)
    export_root = tmp_path / "output"
    export_root.mkdir(parents=True, exist_ok=True)

    with session_factory() as session:
        result = export_project(session, project_id, data_root, export_root)

    snapshots = json.loads(Path(result["snapshots"]).read_text())
    assert len(snapshots) == 1

    snap = snapshots[0]
    assert snap["attempt_id"] == attempt_id
    assert snap["prompt_ko"] == "한국어 프롬프트"
    assert snap["prompt_en"] == "English prompt"
    assert snap["seed"] == 42
    assert snap["workflow_template_id"] is None
    assert snap["execution_mode_id"] is None
    assert snap["param_overrides"] == json.dumps({"steps": 30})
    assert snap["workflow_snapshot"] == json.dumps({"node": "data"})
    assert snap["output_metadata"] == {
        "filename": "clip.mp4",
        "subfolder": "videos",
        "type": "output",
    }


# ---------------------------------------------------------------------------
# Test 4: POST /export/projects/{id} → 200 + ExportResult JSON
# ---------------------------------------------------------------------------


def test_export_api_endpoint(api_client, session_factory):
    client, settings = api_client
    project_id = _create_project(session_factory)
    shot_id = _create_shot(session_factory, project_id, order=1, lyrics="Verse 1")
    attempt_id = _create_attempt(
        session_factory, shot_id, AttemptStatus.NEEDS_REVIEW.value,
        prompt_en="test prompt"
    )
    _select_attempt(session_factory, shot_id, attempt_id)

    response = client.post(f"/api/export/projects/{project_id}")

    assert response.status_code == 200
    data = response.json()
    assert "export_dir" in data
    assert "clip_count" in data
    assert "shot_list" in data
    assert "snapshots" in data
    assert data["clip_count"] == 0  # no actual files on disk

    # Verify files were created
    assert Path(data["shot_list"]).exists()
    assert Path(data["snapshots"]).exists()

    shot_list = json.loads(Path(data["shot_list"]).read_text())
    assert len(shot_list) == 1
    assert shot_list[0]["order"] == 1
    assert shot_list[0]["prompt_en"] == "test prompt"
