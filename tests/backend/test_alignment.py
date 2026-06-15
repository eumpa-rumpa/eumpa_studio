"""Tests for audio alignment job and draft shot generation."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from eumpa_studio.config import Settings
from eumpa_studio.db.base import Base
from eumpa_studio.db.session import get_session
from eumpa_studio.domain.models import Project, Shot
from eumpa_studio.domain.statuses import JobStatus, ShotStatus
from eumpa_studio.execution.align import (
    AlignmentResult,
    create_draft_shots,
    parse_alignment_output,
    run_alignment_job,
)
from eumpa_studio.server.app import app
from eumpa_studio.server.deps import get_settings_dep

# ---------------------------------------------------------------------------
# Pure parsing unit tests (no DB)
# ---------------------------------------------------------------------------


def test_parse_json_array_format():
    """parse_alignment_output handles a JSON array of segment objects."""
    data = json.dumps(
        [
            {"start": 0.0, "end": 2.5, "duration": 2.5, "speaker": "A", "text": "Hello world"},
            {"start": 2.5, "end": 5.0, "duration": 2.5, "speaker": "A", "text": "Second line"},
        ]
    )
    results = parse_alignment_output(data)

    assert len(results) == 2
    assert results[0].start == 0.0
    assert results[0].end == 2.5
    assert results[0].duration == 2.5
    assert results[0].speaker == "A"
    assert results[0].lyrics == "Hello world"
    assert results[1].start == 2.5
    assert results[1].lyrics == "Second line"


def test_parse_jsonl_format():
    """parse_alignment_output handles newline-delimited JSON objects (JSONL)."""
    lines = "\n".join(
        [
            json.dumps({"start": 0.0, "end": 1.0, "speaker": "B", "text": "Line one"}),
            json.dumps({"start": 1.0, "end": 3.5, "speaker": "B", "text": "Line two"}),
        ]
    )
    results = parse_alignment_output(lines)

    assert len(results) == 2
    assert results[0].start == 0.0
    assert results[0].end == 1.0
    assert results[0].lyrics == "Line one"
    assert results[1].start == 1.0
    assert results[1].end == 3.5
    assert results[1].lyrics == "Line two"


def test_parse_computes_duration_if_missing():
    """Duration is computed as end - start when the field is absent."""
    data = json.dumps([{"start": 1.0, "end": 4.0}])
    results = parse_alignment_output(data)

    assert len(results) == 1
    assert results[0].duration == pytest.approx(3.0)


def test_parse_raises_on_invalid_json():
    """ValueError is raised when the output cannot be parsed as JSON."""
    with pytest.raises(ValueError, match="Invalid JSON"):
        parse_alignment_output("not valid json at all")


def test_parse_optional_speaker_and_lyrics():
    """Missing speaker and text/lyrics fields are represented as None."""
    data = json.dumps([{"start": 0.0, "end": 2.0, "duration": 2.0}])
    results = parse_alignment_output(data)

    assert len(results) == 1
    assert results[0].speaker is None
    assert results[0].lyrics is None


# ---------------------------------------------------------------------------
# Integration test fixtures (in-memory SQLite)
# ---------------------------------------------------------------------------


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
def db_session(db_engine):
    Session_ = sessionmaker(bind=db_engine)
    with Session_() as session:
        yield session


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


def _make_project(session: Session, name: str = "Test Project") -> Project:
    project = Project(name=name)
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


# ---------------------------------------------------------------------------
# Integration tests
# ---------------------------------------------------------------------------


def test_create_draft_shots(db_session: Session):
    """create_draft_shots persists 3 Shot rows with correct order and fields."""
    project = _make_project(db_session)

    alignment_results = [
        AlignmentResult(start=0.0, end=2.0, duration=2.0, speaker="A", lyrics="Verse one"),
        AlignmentResult(start=2.0, end=4.5, duration=2.5, speaker="B", lyrics="Verse two"),
        AlignmentResult(start=4.5, end=7.0, duration=2.5, speaker=None, lyrics=None),
    ]

    shots = create_draft_shots(db_session, project.id, alignment_results)

    assert len(shots) == 3

    # Verify IDs were assigned (flush happened).
    assert all(s.id for s in shots)

    # Verify order is 0-based.
    assert shots[0].order == 0
    assert shots[1].order == 1
    assert shots[2].order == 2

    # Verify field mapping.
    assert shots[0].start_time == 0.0
    assert shots[0].end_time == 2.0
    assert shots[0].duration == 2.0
    assert shots[0].speaker == "A"
    assert shots[0].lyrics_text == "Verse one"
    assert shots[0].status == ShotStatus.NEEDS_INPUT.value

    assert shots[1].speaker == "B"
    assert shots[2].speaker is None
    assert shots[2].lyrics_text is None

    # Confirm rows are actually in the database.
    rows = db_session.scalars(
        select(Shot).where(Shot.project_id == project.id).order_by(Shot.order)
    ).all()
    assert len(rows) == 3


def test_alignment_job_failure_preserves_existing_shots(db_session: Session, test_settings: Settings):
    """run_alignment_job failure must not delete pre-existing shots."""
    project = _make_project(db_session)

    # Pre-create 2 shots.
    for i in range(2):
        shot = Shot(
            project_id=project.id,
            order=i,
            start_time=float(i),
            end_time=float(i + 1),
            duration=1.0,
            status=ShotStatus.NEEDS_INPUT.value,
        )
        db_session.add(shot)
    db_session.commit()

    pre_existing = db_session.scalars(
        select(Shot).where(Shot.project_id == project.id)
    ).all()
    assert len(pre_existing) == 2

    # Give the project an audio path so run_alignment_job proceeds to run_alignment.
    project.audio_relative_path = "fake/audio.mp3"
    db_session.commit()

    # Mock run_alignment to raise so the job fails.
    with patch(
        "eumpa_studio.execution.align.run_alignment",
        side_effect=RuntimeError("alignment failed"),
    ):
        try:
            run_alignment_job(db_session, project.id, test_settings)
        except RuntimeError:
            pass

    # Original 2 shots must still be present.
    after = db_session.scalars(
        select(Shot).where(Shot.project_id == project.id)
    ).all()
    assert len(after) == 2


def test_align_api_endpoint(api_client: TestClient, db_engine):
    """POST /api/projects/{id}/align returns 201 + JobRead with type='align'."""
    # First create a project via the API.
    create_resp = api_client.post("/api/projects", data={"name": "Align Test Project"})
    assert create_resp.status_code == 201
    project_id = create_resp.json()["id"]

    # Enqueue an alignment job.
    align_resp = api_client.post(f"/api/projects/{project_id}/align")

    assert align_resp.status_code == 201
    body = align_resp.json()
    assert body["type"] == "align"
    assert body["target_entity_type"] == "project"
    assert body["target_entity_id"] == project_id
    assert body["status"] == JobStatus.PENDING.value
    assert body["id"]


def test_enqueue_unknown_job_type_returns_422(api_client: TestClient):
    """POST /api/jobs with an unknown type returns 422."""
    resp = api_client.post(
        "/api/jobs",
        json={"type": "bogus_type", "target_entity_type": "project", "target_entity_id": "x"},
    )
    assert resp.status_code == 422
