"""Tests for SQLAlchemy ORM models (sync, in-memory SQLite)."""

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from eumpa_studio.db.base import Base
from eumpa_studio.domain.models import (
    Asset,
    Attempt,
    ExecutionMode,
    Job,
    Project,
    Shot,
    WorkflowTemplate,
)
from eumpa_studio.domain.statuses import AttemptStatus, JobStatus, ShotStatus


@pytest.fixture(scope="module")
def db_session():
    """Create an in-memory SQLite engine, build all tables, yield a session."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session_ = sessionmaker(bind=engine)
    session = Session_()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


# ---------------------------------------------------------------------------
# Project
# ---------------------------------------------------------------------------


def test_create_project(db_session: Session):
    project = Project(
        name="My MV Project",
        audio_storage_backend="local",
        audio_relative_path="audio/track.wav",
        lyrics_text="Hello world",
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    assert project.id is not None
    assert len(project.id) == 36  # UUID string
    assert project.name == "My MV Project"
    assert project.audio_storage_backend == "local"
    assert project.audio_relative_path == "audio/track.wav"
    assert project.lyrics_text == "Hello world"
    assert project.lyrics_storage_backend is None
    assert project.default_comfyui_server is None


def test_project_optional_fields(db_session: Session):
    project = Project(
        name="Full Project",
        audio_storage_backend="comfyui",
        audio_relative_path="audio/full.mp3",
        lyrics_storage_backend="local",
        lyrics_relative_path="lyrics/full.txt",
        visual_bible_text="Visual bible content",
        visual_bible_storage_backend="local",
        visual_bible_relative_path="vb/full.pdf",
        default_comfyui_server="http://localhost:8188",
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    assert project.lyrics_storage_backend == "local"
    assert project.lyrics_relative_path == "lyrics/full.txt"
    assert project.visual_bible_text == "Visual bible content"
    assert project.default_comfyui_server == "http://localhost:8188"


# ---------------------------------------------------------------------------
# Shot
# ---------------------------------------------------------------------------


def test_create_shot(db_session: Session):
    project = Project(
        name="Shot Project",
        audio_storage_backend="local",
        audio_relative_path="audio/shot.wav",
    )
    db_session.add(project)
    db_session.commit()

    shot = Shot(
        project_id=project.id,
        order=0,
        start_time=0.0,
        end_time=5.0,
        duration=5.0,
        speaker="vocalist",
        lyrics_text="First verse",
        shot_note="Close-up on singer",
        status=ShotStatus.NEEDS_INPUT.value,
    )
    db_session.add(shot)
    db_session.commit()
    db_session.refresh(shot)

    assert shot.id is not None
    assert shot.project_id == project.id
    assert shot.order == 0
    assert shot.start_time == 0.0
    assert shot.end_time == 5.0
    assert shot.duration == 5.0
    assert shot.speaker == "vocalist"
    assert shot.status == ShotStatus.NEEDS_INPUT.value
    assert shot.active_attempt_id is None


# ---------------------------------------------------------------------------
# Attempt
# ---------------------------------------------------------------------------


def test_create_attempt(db_session: Session):
    project = Project(
        name="Attempt Project",
        audio_storage_backend="local",
        audio_relative_path="audio/attempt.wav",
    )
    db_session.add(project)
    db_session.commit()

    shot = Shot(
        project_id=project.id,
        order=1,
        start_time=5.0,
        end_time=10.0,
        duration=5.0,
    )
    db_session.add(shot)
    db_session.commit()

    attempt = Attempt(
        shot_id=shot.id,
        prompt_ko="한국어 프롬프트",
        prompt_en="English prompt",
        seed=42,
        status=AttemptStatus.NEEDS_INPUT.value,
        image_storage_backend="comfyui",
        image_relative_path="output/img_001.png",
    )
    db_session.add(attempt)
    db_session.commit()
    db_session.refresh(attempt)

    assert attempt.id is not None
    assert attempt.shot_id == shot.id
    assert attempt.prompt_ko == "한국어 프롬프트"
    assert attempt.prompt_en == "English prompt"
    assert attempt.seed == 42
    assert attempt.status == AttemptStatus.NEEDS_INPUT.value
    assert attempt.image_storage_backend == "comfyui"
    assert attempt.parent_attempt_id is None
    assert attempt.workflow_template_id is None


def test_attempt_self_reference(db_session: Session):
    """An attempt can reference a parent attempt."""
    project = Project(
        name="SelfRef Project",
        audio_storage_backend="local",
        audio_relative_path="audio/selfref.wav",
    )
    db_session.add(project)
    db_session.commit()

    shot = Shot(
        project_id=project.id,
        order=2,
        start_time=10.0,
        end_time=15.0,
        duration=5.0,
    )
    db_session.add(shot)
    db_session.commit()

    parent = Attempt(shot_id=shot.id, status=AttemptStatus.REJECTED.value)
    db_session.add(parent)
    db_session.commit()

    child = Attempt(
        shot_id=shot.id,
        parent_attempt_id=parent.id,
        status=AttemptStatus.NEEDS_INPUT.value,
    )
    db_session.add(child)
    db_session.commit()
    db_session.refresh(child)

    assert child.parent_attempt_id == parent.id


# ---------------------------------------------------------------------------
# Asset
# ---------------------------------------------------------------------------


def test_create_asset(db_session: Session):
    project = Project(
        name="Asset Project",
        audio_storage_backend="local",
        audio_relative_path="audio/asset.wav",
    )
    db_session.add(project)
    db_session.commit()

    asset = Asset(
        project_id=project.id,
        name="reference_image.jpg",
        storage_backend="local",
        relative_path="assets/reference_image.jpg",
        mime_type="image/jpeg",
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)

    assert asset.id is not None
    assert asset.project_id == project.id
    assert asset.name == "reference_image.jpg"
    assert asset.storage_backend == "local"
    assert asset.relative_path == "assets/reference_image.jpg"
    assert asset.mime_type == "image/jpeg"


# ---------------------------------------------------------------------------
# WorkflowTemplate
# ---------------------------------------------------------------------------


def test_create_workflow_template(db_session: Session):
    template = WorkflowTemplate(
        name="img2video_v1",
        json_path="workflows/img2video_v1.json",
        file_hash="abc123",
        version="1.0",
        compatibility_notes="Requires AnimateDiff node",
    )
    db_session.add(template)
    db_session.commit()
    db_session.refresh(template)

    assert template.id is not None
    assert template.name == "img2video_v1"
    assert template.json_path == "workflows/img2video_v1.json"
    assert template.file_hash == "abc123"
    assert template.version == "1.0"
    assert template.compatibility_notes == "Requires AnimateDiff node"


# ---------------------------------------------------------------------------
# ExecutionMode
# ---------------------------------------------------------------------------


def test_create_execution_mode(db_session: Session):
    template = WorkflowTemplate(
        name="text2img_v1",
        json_path="workflows/text2img_v1.json",
    )
    db_session.add(template)
    db_session.commit()

    mode = ExecutionMode(
        workflow_template_id=template.id,
        name="standard",
        required_inputs=json.dumps(["prompt_en", "seed"]),
        optional_inputs=json.dumps(["cfg", "steps"]),
        node_bindings=json.dumps({"KSampler": {"seed": "$seed"}}),
        validation_rules=json.dumps({}),
        exposed_params=json.dumps(["seed", "cfg", "steps"]),
    )
    db_session.add(mode)
    db_session.commit()
    db_session.refresh(mode)

    assert mode.id is not None
    assert mode.workflow_template_id == template.id
    assert mode.name == "standard"
    assert json.loads(mode.required_inputs) == ["prompt_en", "seed"]
    assert json.loads(mode.node_bindings) == {"KSampler": {"seed": "$seed"}}


# ---------------------------------------------------------------------------
# Job
# ---------------------------------------------------------------------------


def test_create_job(db_session: Session):
    job = Job(
        type="render",
        target_entity_type="attempt",
        target_entity_id="some-uuid-1234",
        status=JobStatus.PENDING.value,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    assert job.id is not None
    assert job.type == "render"
    assert job.target_entity_type == "attempt"
    assert job.target_entity_id == "some-uuid-1234"
    assert job.status == JobStatus.PENDING.value
    assert job.logs is None
    assert job.error is None
    assert job.started_at is None
    assert job.finished_at is None


def test_job_status_transitions(db_session: Session):
    job = Job(type="align", status=JobStatus.PENDING.value)
    db_session.add(job)
    db_session.commit()

    job.status = JobStatus.RUNNING.value
    db_session.commit()
    db_session.refresh(job)
    assert job.status == JobStatus.RUNNING.value

    job.status = JobStatus.DONE.value
    db_session.commit()
    db_session.refresh(job)
    assert job.status == JobStatus.DONE.value


# ---------------------------------------------------------------------------
# Status enum values
# ---------------------------------------------------------------------------


def test_shot_status_enum_values():
    assert ShotStatus.NEEDS_INPUT.value == "Needs Input"
    assert ShotStatus.READY.value == "Ready"
    assert ShotStatus.QUEUED.value == "Queued"
    assert ShotStatus.RENDERING.value == "Rendering"
    assert ShotStatus.NEEDS_REVIEW.value == "Needs Review"
    assert ShotStatus.SELECTED.value == "Selected"
    assert ShotStatus.REDO.value == "Redo"
    assert ShotStatus.REJECTED.value == "Rejected"
    assert ShotStatus.FAILED.value == "Failed"


def test_attempt_status_enum_values():
    assert AttemptStatus.NEEDS_INPUT.value == "Needs Input"
    assert AttemptStatus.SELECTED.value == "Selected"
    assert AttemptStatus.FAILED.value == "Failed"


def test_job_status_enum_values():
    assert JobStatus.PENDING.value == "pending"
    assert JobStatus.RUNNING.value == "running"
    assert JobStatus.DONE.value == "done"
    assert JobStatus.FAILED.value == "failed"


# ---------------------------------------------------------------------------
# Relationship traversal
# ---------------------------------------------------------------------------


def test_project_shots_relationship(db_session: Session):
    project = Project(
        name="Rel Project",
        audio_storage_backend="local",
        audio_relative_path="audio/rel.wav",
    )
    db_session.add(project)
    db_session.commit()

    shot1 = Shot(project_id=project.id, order=0, start_time=0.0, end_time=3.0, duration=3.0)
    shot2 = Shot(project_id=project.id, order=1, start_time=3.0, end_time=6.0, duration=3.0)
    db_session.add_all([shot1, shot2])
    db_session.commit()
    db_session.refresh(project)

    assert len(project.shots) == 2


def test_project_assets_relationship(db_session: Session):
    project = Project(
        name="Asset Rel Project",
        audio_storage_backend="local",
        audio_relative_path="audio/assetrel.wav",
    )
    db_session.add(project)
    db_session.commit()

    asset = Asset(
        project_id=project.id,
        name="logo.png",
        storage_backend="local",
        relative_path="assets/logo.png",
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(project)

    assert len(project.assets) == 1
    assert project.assets[0].name == "logo.png"


def test_workflow_template_execution_modes_relationship(db_session: Session):
    template = WorkflowTemplate(
        name="wf_rel_test",
        json_path="workflows/wf_rel_test.json",
    )
    db_session.add(template)
    db_session.commit()

    mode_a = ExecutionMode(
        workflow_template_id=template.id,
        name="mode_a",
        required_inputs="[]",
        optional_inputs="[]",
        node_bindings="{}",
        validation_rules="{}",
        exposed_params="[]",
    )
    mode_b = ExecutionMode(
        workflow_template_id=template.id,
        name="mode_b",
        required_inputs="[]",
        optional_inputs="[]",
        node_bindings="{}",
        validation_rules="{}",
        exposed_params="[]",
    )
    db_session.add_all([mode_a, mode_b])
    db_session.commit()
    db_session.refresh(template)

    assert len(template.execution_modes) == 2
