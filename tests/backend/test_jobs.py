"""Tests for persistent job queue execution."""

import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from eumpa_studio.db.base import Base
from eumpa_studio.db.session import get_session
from eumpa_studio.domain.models import Attempt, ExecutionMode, Job, Project, Shot, WorkflowTemplate
from eumpa_studio.domain.statuses import JobStatus
from eumpa_studio.execution.jobs import AppJobRunner
from eumpa_studio.execution.worker import WorkerLoop
from eumpa_studio.server.app import app


@pytest.fixture()
def session_factory():
    """Create an in-memory SQLite database shared across worker sessions."""
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


@pytest.fixture()
def api_client(session_factory):
    def override_get_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def enqueue_job(
    session: Session,
    job_type: str,
    target_entity_id: str,
    created_at: datetime.datetime | None = None,
) -> Job:
    job_kwargs = {}
    if created_at is not None:
        job_kwargs["created_at"] = created_at

    job = Job(
        type=job_type,
        target_entity_type="shot",
        target_entity_id=target_entity_id,
        status=JobStatus.PENDING.value,
        **job_kwargs,
    )
    session.add(job)
    session.commit()
    session.refresh(job)
    return job


def get_job(session: Session, job_id: str) -> Job:
    job = session.get(Job, job_id)
    assert job is not None
    return job


def test_worker_marks_job_running_then_done(session_factory):
    transitions: list[tuple[str, str | None]] = []

    with session_factory() as session:
        job = enqueue_job(session, "render_attempt", "shot-1")
        job_id = job.id

    def runner(job_type: str, target_entity_id: str | None) -> None:
        transitions.append((job_type, target_entity_id))
        with session_factory() as session:
            running_job = get_job(session, job_id)
            assert running_job.status == JobStatus.RUNNING.value
            assert running_job.started_at is not None
            assert running_job.finished_at is None

    worker = WorkerLoop(session_factory=session_factory, runner=runner)

    assert worker.run_once() is True

    with session_factory() as session:
        completed_job = get_job(session, job_id)
        assert completed_job.status == JobStatus.DONE.value
        assert completed_job.error is None
        assert completed_job.started_at is not None
        assert completed_job.finished_at is not None
        assert transitions == [("render_attempt", "shot-1")]


def test_worker_continues_to_next_job_after_failure(session_factory):
    calls: list[tuple[str, str | None]] = []
    queue_time = datetime.datetime(2026, 1, 1, 12, 0, 0)

    with session_factory() as session:
        first = enqueue_job(session, "render_attempt", "shot-1", queue_time)
        second = enqueue_job(
            session,
            "render_attempt",
            "shot-2",
            queue_time + datetime.timedelta(microseconds=1),
        )
        first_id = first.id
        second_id = second.id

    def runner(job_type: str, target_entity_id: str | None) -> None:
        calls.append((job_type, target_entity_id))
        if target_entity_id == "shot-1":
            raise RuntimeError("render failed")

    worker = WorkerLoop(session_factory=session_factory, runner=runner)

    assert worker.run_once() is True
    assert worker.run_once() is True
    assert worker.run_once() is False

    with session_factory() as session:
        failed_job = get_job(session, first_id)
        completed_job = get_job(session, second_id)
        ordered_jobs = session.scalars(select(Job).order_by(Job.created_at, Job.id)).all()

        assert failed_job.status == JobStatus.FAILED.value
        assert failed_job.error == "render failed"
        assert failed_job.finished_at is not None

        assert completed_job.status == JobStatus.DONE.value
        assert completed_job.error is None
        assert completed_job.finished_at is not None

        assert [job.id for job in ordered_jobs] == [first_id, second_id]
        assert calls == [("render_attempt", "shot-1"), ("render_attempt", "shot-2")]


def test_jobs_api_enqueues_lists_and_gets_jobs(api_client: TestClient):
    create_response = api_client.post(
        "/api/jobs",
        json={
            "type": "render_attempt",
            "target_entity_type": "shot",
            "target_entity_id": "shot-1",
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created["id"]
    assert created["type"] == "render_attempt"
    assert created["target_entity_type"] == "shot"
    assert created["target_entity_id"] == "shot-1"
    assert created["status"] == JobStatus.PENDING.value
    assert created["created_at"]
    assert created["updated_at"]

    list_response = api_client.get("/api/jobs")

    assert list_response.status_code == 200
    jobs = list_response.json()
    assert [job["id"] for job in jobs] == [created["id"]]

    get_response = api_client.get(f"/api/jobs/{created['id']}")

    assert get_response.status_code == 200
    assert get_response.json() == created


def test_alignment_job_rejects_missing_project(api_client: TestClient):
    response = api_client.post("/api/projects/missing-project-id/align")

    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


def test_app_job_runner_dispatches_align_and_render(session_factory):
    class Settings:
        comfyui_url = "http://comfy.local:8188"
        alignment_command = "align"
        data_root = "."

    calls: list[tuple[str, str, str, str | None]] = []

    def align_runner(session: Session, project_id: str, settings: Settings) -> None:
        calls.append(("align", project_id, settings.alignment_command, None))

    def render_runner(
        session: Session,
        attempt_id: str,
        comfyui_url: str,
        data_root,
    ) -> None:
        calls.append(("render", attempt_id, comfyui_url, str(data_root)))

    runner = AppJobRunner(
        session_factory=session_factory,
        settings=Settings(),
        align_runner=align_runner,
        render_runner=render_runner,
    )

    runner("align", "project-1")
    runner("render", "attempt-1")
    runner("render_attempt", "attempt-2")

    assert calls == [
        ("align", "project-1", "align", None),
        ("render", "attempt-1", "http://comfy.local:8188", "."),
        ("render", "attempt-2", "http://comfy.local:8188", "."),
    ]


def test_render_attempt_endpoint_requires_workflow_configuration(
    api_client: TestClient,
    session_factory,
):
    with session_factory() as session:
        project = Project(name="Render Project")
        session.add(project)
        session.commit()
        shot = Shot(
            project_id=project.id,
            order=0,
            start_time=0,
            end_time=5,
            duration=5,
        )
        session.add(shot)
        session.commit()
        attempt = Attempt(shot_id=shot.id)
        session.add(attempt)
        session.commit()
        shot_id = shot.id
        attempt_id = attempt.id

    response = api_client.post(f"/api/shots/{shot_id}/attempts/{attempt_id}/render")

    assert response.status_code == 422
    assert "workflow" in response.json()["detail"]


def test_render_attempt_endpoint_enqueues_configured_attempt(
    api_client: TestClient,
    session_factory,
    tmp_path,
):
    workflow_path = tmp_path / "workflow.json"
    workflow_path.write_text('{"1": {"class_type": "TestNode", "inputs": {}}}', encoding="utf-8")

    with session_factory() as session:
        project = Project(name="Configured Render Project")
        session.add(project)
        session.commit()
        shot = Shot(
            project_id=project.id,
            order=0,
            start_time=0,
            end_time=5,
            duration=5,
        )
        template = WorkflowTemplate(name="LTX", json_path=str(workflow_path))
        session.add_all([shot, template])
        session.commit()
        mode = ExecutionMode(
            workflow_template_id=template.id,
            name="Image to video",
            required_inputs='["image", "prompt_en"]',
            node_bindings="{}",
        )
        session.add(mode)
        session.commit()
        attempt = Attempt(
            shot_id=shot.id,
            workflow_template_id=template.id,
            execution_mode_id=mode.id,
        )
        session.add(attempt)
        session.commit()
        shot_id = shot.id
        attempt_id = attempt.id

    response = api_client.post(f"/api/shots/{shot_id}/attempts/{attempt_id}/render")

    assert response.status_code == 201
    body = response.json()
    assert body["type"] == "render"
    assert body["target_entity_type"] == "attempt"
    assert body["target_entity_id"] == attempt_id
    assert body["status"] == JobStatus.PENDING.value


def test_render_attempt_endpoint_rejects_missing_workflow_file(
    api_client: TestClient,
    session_factory,
    tmp_path,
):
    missing_workflow_path = tmp_path / "missing-workflow.json"

    with session_factory() as session:
        project = Project(name="Broken Render Project")
        session.add(project)
        session.commit()
        shot = Shot(
            project_id=project.id,
            order=0,
            start_time=0,
            end_time=5,
            duration=5,
        )
        template = WorkflowTemplate(name="Missing LTX", json_path=str(missing_workflow_path))
        session.add_all([shot, template])
        session.commit()
        mode = ExecutionMode(
            workflow_template_id=template.id,
            name="Image to video",
            required_inputs='["image", "prompt_en"]',
            node_bindings="{}",
        )
        session.add(mode)
        session.commit()
        attempt = Attempt(
            shot_id=shot.id,
            workflow_template_id=template.id,
            execution_mode_id=mode.id,
        )
        session.add(attempt)
        session.commit()
        shot_id = shot.id
        attempt_id = attempt.id

    response = api_client.post(f"/api/shots/{shot_id}/attempts/{attempt_id}/render")

    assert response.status_code == 422
    assert "Workflow template file not found" in response.json()["detail"]
