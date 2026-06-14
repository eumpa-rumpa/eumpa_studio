"""Tests for ComfyUI render submission and result metadata."""

import json

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from eumpa_studio.db.base import Base
from eumpa_studio.domain.models import Attempt, ExecutionMode, Project, Shot, WorkflowTemplate
from eumpa_studio.domain.statuses import AttemptStatus
from eumpa_studio.execution.comfy_client import run_render_job, submit_render
from eumpa_studio.execution.workflow_patch import ValidationError


@pytest.fixture()
def session_factory():
    """Create an in-memory SQLite database shared across sessions."""
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


def _response(status_code: int, payload: dict) -> httpx.Response:
    return httpx.Response(
        status_code,
        json=payload,
        request=httpx.Request("GET", "http://comfyui.test"),
    )


class FakeComfyClient:
    post_response: httpx.Response = _response(200, {"prompt_id": "abc"})
    history_responses: list[httpx.Response] = []
    posts: list[tuple[str, dict]] = []
    gets: list[str] = []

    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, url: str, json: dict) -> httpx.Response:
        self.__class__.posts.append((url, json))
        return self.__class__.post_response

    def get(self, url: str) -> httpx.Response:
        self.__class__.gets.append(url)
        if self.__class__.history_responses:
            return self.__class__.history_responses.pop(0)
        return _response(200, {})


@pytest.fixture(autouse=True)
def fake_httpx_client(monkeypatch):
    FakeComfyClient.post_response = _response(200, {"prompt_id": "abc"})
    FakeComfyClient.history_responses = []
    FakeComfyClient.posts = []
    FakeComfyClient.gets = []
    monkeypatch.setattr("eumpa_studio.execution.comfy_client.httpx.Client", FakeComfyClient)


@pytest.fixture(autouse=True)
def no_poll_sleep(monkeypatch):
    monkeypatch.setattr("eumpa_studio.execution.comfy_client.time.sleep", lambda seconds: None)


def create_attempt(
    session: Session,
    tmp_path,
    *,
    execution_mode: bool = True,
    workflow_file: bool = True,
) -> Attempt:
    project = Project(
        name="Render Project",
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

    workflow_path = tmp_path / "workflow.json"
    if workflow_file:
        workflow_path.write_text(
            json.dumps(
                {
                    "1": {"inputs": {"image": ""}},
                    "2": {"inputs": {"text": ""}},
                    "3": {"inputs": {"seed": 0}},
                }
            ),
            encoding="utf-8",
        )

    template = WorkflowTemplate(
        name="img2video",
        json_path=str(workflow_path),
    )
    session.add(template)
    session.flush()

    mode = None
    if execution_mode:
        mode = ExecutionMode(
            workflow_template_id=template.id,
            name="standard",
            required_inputs=json.dumps(["image", "prompt_en"]),
            optional_inputs=json.dumps(["seed", "cfg"]),
            node_bindings=json.dumps(
                {
                    "image": {"node_id": "1", "field": "image"},
                    "prompt_en": {"node_id": "2", "field": "text"},
                    "seed": {"node_id": "3", "field": "seed"},
                    "cfg": {"node_id": "3", "field": "cfg"},
                }
            ),
            validation_rules=json.dumps({}),
            exposed_params=json.dumps(["seed", "cfg"]),
        )
        session.add(mode)
        session.flush()

    attempt = Attempt(
        shot_id=shot.id,
        image_storage_backend="local",
        image_relative_path="images/input.png",
        prompt_en="A singer under neon stage lights",
        seed=1234,
        workflow_template_id=template.id,
        execution_mode_id=mode.id if mode is not None else None,
        param_overrides=json.dumps({"cfg": 7.5}),
        status=AttemptStatus.QUEUED.value,
    )
    session.add(attempt)
    session.commit()
    session.refresh(attempt)
    return attempt


def test_submit_render_success(session_factory, tmp_path):
    FakeComfyClient.history_responses = [
        _response(
            200,
            {
                "abc": {
                    "outputs": {
                        "9": {
                            "images": [
                                {
                                    "filename": "render_0001.png",
                                    "subfolder": "final",
                                    "type": "output",
                                }
                            ]
                        }
                    }
                }
            },
        )
    ]

    with session_factory() as session:
        attempt = create_attempt(session, tmp_path)
        output = submit_render(session, attempt.id, "http://comfyui.test")

        refreshed = session.get(Attempt, attempt.id)
        assert refreshed is not None
        assert output.filename == "render_0001.png"
        assert output.subfolder == "final"
        assert output.type == "output"
        assert output.server_id == "http://comfyui.test"
        assert refreshed.comfyui_prompt_id == "abc"
        assert json.loads(refreshed.output_metadata) == {
            "filename": "render_0001.png",
            "subfolder": "final",
            "type": "output",
            "server_id": "http://comfyui.test",
        }
        assert refreshed.status == AttemptStatus.NEEDS_REVIEW.value
        assert json.loads(refreshed.workflow_snapshot) == {
            "1": {"inputs": {"image": "images/input.png"}},
            "2": {"inputs": {"text": "A singer under neon stage lights"}},
            "3": {"inputs": {"seed": 1234, "cfg": 7.5}},
        }
        assert FakeComfyClient.posts == [
            (
                "http://comfyui.test/prompt",
                {
                    "prompt": json.loads(refreshed.workflow_snapshot),
                    "client_id": attempt.id,
                },
            )
        ]
        assert FakeComfyClient.gets == ["http://comfyui.test/history/abc"]


def test_submit_render_validation_error(session_factory, tmp_path):
    with session_factory() as session:
        attempt = create_attempt(session, tmp_path, execution_mode=False)

        with pytest.raises((ValidationError, ValueError)):
            submit_render(session, attempt.id, "http://comfyui.test")

        refreshed = session.get(Attempt, attempt.id)
        assert refreshed is not None
        assert refreshed.status == AttemptStatus.FAILED.value


def test_submit_render_comfyui_error(session_factory, tmp_path):
    FakeComfyClient.post_response = _response(500, {"error": "boom"})

    with session_factory() as session:
        attempt = create_attempt(session, tmp_path)

        with pytest.raises(httpx.HTTPStatusError):
            submit_render(session, attempt.id, "http://comfyui.test")

        refreshed = session.get(Attempt, attempt.id)
        assert refreshed is not None
        assert refreshed.status == AttemptStatus.FAILED.value


def test_submit_render_timeout(session_factory, tmp_path):
    FakeComfyClient.history_responses = [_response(200, {"abc": {"outputs": {}}})]

    with session_factory() as session:
        attempt = create_attempt(session, tmp_path)

        with pytest.raises(RuntimeError, match="Timed out"):
            submit_render(session, attempt.id, "http://comfyui.test", timeout=0)

        refreshed = session.get(Attempt, attempt.id)
        assert refreshed is not None
        assert refreshed.status == AttemptStatus.FAILED.value


def test_run_render_job_attempt_not_found(session_factory):
    with session_factory() as session:
        with pytest.raises(ValueError, match="Attempt 'missing' not found"):
            run_render_job(session, "missing", "http://comfyui.test")
