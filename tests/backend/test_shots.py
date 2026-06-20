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
from eumpa_studio.domain.models import Attempt, ExecutionMode, Project, Shot, WorkflowTemplate
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


def test_list_shots_includes_active_attempt_video_url(api_client: TestClient, db_session):
    project = Project(name="Shot Preview Project")
    db_session.add(project)
    db_session.commit()

    shot = Shot(
        project_id=project.id,
        order=0,
        start_time=0.0,
        end_time=2.0,
        duration=2.0,
        status=ShotStatus.NEEDS_REVIEW.value,
    )
    db_session.add(shot)
    db_session.commit()

    attempt = Attempt(
        shot_id=shot.id,
        output_metadata='{"filename": "clip 01.mp4", "subfolder": "renders", "type": "output"}',
        status=AttemptStatus.NEEDS_REVIEW.value,
    )
    db_session.add(attempt)
    db_session.commit()
    shot.active_attempt_id = attempt.id
    db_session.commit()

    response = api_client.get(f"/api/shots?project_id={project.id}")

    assert response.status_code == 200
    body = response.json()
    assert body[0]["active_attempt"]["output_metadata"] == attempt.output_metadata
    assert body[0]["active_attempt"]["video_url"] == (
        "http://localhost:8188/view?filename=clip+01.mp4&subfolder=renders&type=output"
    )


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


def test_update_attempt_prompts(api_client: TestClient, db_session):
    project = Project(name="Prompt Editing Project")
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
        status=AttemptStatus.NEEDS_INPUT.value,
    )
    db_session.add(attempt)
    db_session.commit()

    response = api_client.patch(
        f"/api/shots/{shot.id}/attempts/{attempt.id}",
        json={
            "prompt_ko": "브라우저에서 저장한 한국어 프롬프트",
            "prompt_en": "Prompt saved from the browser",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == attempt.id
    assert body["prompt_ko"] == "브라우저에서 저장한 한국어 프롬프트"
    assert body["prompt_en"] == "Prompt saved from the browser"


def test_update_attempt_workflow_configuration(api_client: TestClient, db_session):
    project = Project(name="Workflow Config Project")
    db_session.add(project)
    db_session.commit()

    shot = Shot(
        project_id=project.id,
        order=0,
        start_time=0.0,
        end_time=2.0,
        duration=2.0,
    )
    template = WorkflowTemplate(name="LTX", json_path="workflow.json")
    db_session.add_all([shot, template])
    db_session.commit()

    mode = ExecutionMode(
        workflow_template_id=template.id,
        name="Image to video",
        required_inputs='["image", "prompt_en"]',
        node_bindings="{}",
    )
    attempt = Attempt(shot_id=shot.id)
    db_session.add_all([mode, attempt])
    db_session.commit()

    response = api_client.patch(
        f"/api/shots/{shot.id}/attempts/{attempt.id}",
        json={
            "workflow_template_id": template.id,
            "execution_mode_id": mode.id,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["workflow_template_id"] == template.id
    assert body["execution_mode_id"] == mode.id


def test_create_attempt_makes_it_active(api_client: TestClient, db_session):
    project = Project(name="Attempt Creation Project")
    db_session.add(project)
    db_session.commit()

    shot = Shot(
        project_id=project.id,
        order=0,
        start_time=0.0,
        end_time=2.0,
        duration=2.0,
        status=ShotStatus.NEEDS_INPUT.value,
    )
    db_session.add(shot)
    db_session.commit()

    response = api_client.post(f"/api/shots/{shot.id}/attempts", json={})

    assert response.status_code == 201
    body = response.json()
    assert body["shot_id"] == shot.id
    assert body["status"] == AttemptStatus.NEEDS_INPUT.value
    assert body["output_metadata"] is None
    db_session.expire_all()
    refreshed_shot = db_session.get(Shot, shot.id)
    assert refreshed_shot is not None
    assert refreshed_shot.active_attempt_id == body["id"]
    assert db_session.get(Attempt, body["id"]) is not None


def test_update_attempt_image_fields(api_client: TestClient, db_session):
    project = Project(name="Attempt Image Update Project")
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

    attempt = Attempt(shot_id=shot.id, status=AttemptStatus.NEEDS_INPUT.value)
    db_session.add(attempt)
    db_session.commit()

    response = api_client.patch(
        f"/api/shots/{shot.id}/attempts/{attempt.id}",
        json={
            "image_storage_backend": "local",
            "image_relative_path": "projects/project-1/assets/reference.png",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["image_storage_backend"] == "local"
    assert body["image_relative_path"] == "projects/project-1/assets/reference.png"

    end_response = api_client.patch(
        f"/api/shots/{shot.id}/attempts/{attempt.id}",
        json={
            "end_image_storage_backend": "local",
            "end_image_relative_path": "projects/project-1/assets/end.png",
        },
    )

    assert end_response.status_code == 200
    end_body = end_response.json()
    assert end_body["end_image_storage_backend"] == "local"
    assert end_body["end_image_relative_path"] == "projects/project-1/assets/end.png"

    clear_response = api_client.patch(
        f"/api/shots/{shot.id}/attempts/{attempt.id}",
        json={
            "end_image_storage_backend": None,
            "end_image_relative_path": None,
        },
    )

    assert clear_response.status_code == 200
    clear_body = clear_response.json()
    assert clear_body["end_image_storage_backend"] is None
    assert clear_body["end_image_relative_path"] is None


def test_duplicate_rendered_attempt_copies_inputs_and_clears_outputs(
    api_client: TestClient,
    db_session,
):
    project = Project(name="Attempt Duplicate Project")
    db_session.add(project)
    db_session.commit()

    shot = Shot(
        project_id=project.id,
        order=0,
        start_time=0.0,
        end_time=2.0,
        duration=2.0,
        status=ShotStatus.NEEDS_REVIEW.value,
    )
    template = WorkflowTemplate(name="LTX", json_path="workflow.json")
    db_session.add_all([shot, template])
    db_session.commit()

    mode = ExecutionMode(
        workflow_template_id=template.id,
        name="Image to video",
        required_inputs='["image", "prompt_en"]',
        node_bindings="{}",
    )
    db_session.add(mode)
    db_session.commit()

    attempt = Attempt(
        shot_id=shot.id,
        image_storage_backend="local",
        image_relative_path="projects/project-1/assets/reference.png",
        shot_note_snapshot="wide shot",
        prompt_ko="원본 프롬프트",
        prompt_en="Original prompt",
        workflow_template_id=template.id,
        execution_mode_id=mode.id,
        param_overrides='{"steps": 8}',
        seed=123,
        workflow_snapshot='{"nodes": []}',
        comfyui_prompt_id="prompt-1",
        output_metadata='{"filename": "output.mp4"}',
        review_note="approved later",
        status=AttemptStatus.NEEDS_REVIEW.value,
    )
    db_session.add(attempt)
    db_session.commit()

    response = api_client.post(f"/api/shots/{shot.id}/attempts/{attempt.id}/duplicate")

    assert response.status_code == 201
    body = response.json()
    assert body["id"] != attempt.id
    assert body["parent_attempt_id"] == attempt.id
    assert body["image_storage_backend"] == "local"
    assert body["image_relative_path"] == "projects/project-1/assets/reference.png"
    assert body["shot_note_snapshot"] == "wide shot"
    assert body["prompt_ko"] == "원본 프롬프트"
    assert body["prompt_en"] == "Original prompt"
    assert body["workflow_template_id"] == template.id
    assert body["execution_mode_id"] == mode.id
    assert body["param_overrides"] == '{"steps": 8}'
    assert body["seed"] == 123
    assert body["workflow_snapshot"] is None
    assert body["comfyui_prompt_id"] is None
    assert body["output_metadata"] is None
    assert body["review_note"] is None
    assert body["status"] == AttemptStatus.NEEDS_INPUT.value
    db_session.expire_all()
    refreshed_shot = db_session.get(Shot, shot.id)
    assert refreshed_shot is not None
    assert refreshed_shot.active_attempt_id == body["id"]


def test_rendered_attempt_rejects_input_mutation(api_client: TestClient, db_session):
    project = Project(name="Rendered Attempt Guard Project")
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
        prompt_en="Original prompt",
        output_metadata='{"filename": "output.mp4"}',
        status=AttemptStatus.NEEDS_REVIEW.value,
    )
    db_session.add(attempt)
    db_session.commit()

    response = api_client.patch(
        f"/api/shots/{shot.id}/attempts/{attempt.id}",
        json={"prompt_en": "Changed prompt"},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Duplicate rendered attempts before changing inputs"
    db_session.expire_all()
    refreshed_attempt = db_session.get(Attempt, attempt.id)
    assert refreshed_attempt is not None
    assert refreshed_attempt.prompt_en == "Original prompt"


def test_rendered_attempt_allows_review_note_update(api_client: TestClient, db_session):
    project = Project(name="Rendered Attempt Review Note Project")
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
        output_metadata='{"filename": "output.mp4"}',
        status=AttemptStatus.NEEDS_REVIEW.value,
    )
    db_session.add(attempt)
    db_session.commit()

    response = api_client.patch(
        f"/api/shots/{shot.id}/attempts/{attempt.id}",
        json={"review_note": "keep this render"},
    )

    assert response.status_code == 200
    assert response.json()["review_note"] == "keep this render"


@pytest.mark.parametrize(
    ("review_status", "expected_shot_status"),
    [
        (AttemptStatus.SELECTED.value, ShotStatus.SELECTED.value),
        (AttemptStatus.REDO.value, ShotStatus.REDO.value),
        (AttemptStatus.REJECTED.value, ShotStatus.REJECTED.value),
        (AttemptStatus.FAILED.value, ShotStatus.FAILED.value),
    ],
)
def test_review_active_attempt_updates_parent_shot_status(
    api_client: TestClient,
    db_session,
    review_status: str,
    expected_shot_status: str,
):
    project = Project(name=f"Review Status {review_status} Project")
    db_session.add(project)
    db_session.commit()

    shot = Shot(
        project_id=project.id,
        order=0,
        start_time=0.0,
        end_time=2.0,
        duration=2.0,
        status=ShotStatus.NEEDS_REVIEW.value,
    )
    db_session.add(shot)
    db_session.commit()

    attempt = Attempt(
        shot_id=shot.id,
        output_metadata='{"filename": "output.mp4"}',
        status=AttemptStatus.NEEDS_REVIEW.value,
    )
    db_session.add(attempt)
    db_session.commit()
    shot.active_attempt_id = attempt.id
    db_session.commit()

    response = api_client.post(
        f"/api/shots/{shot.id}/attempts/{attempt.id}/review",
        json={"status": review_status},
    )

    assert response.status_code == 200
    db_session.expire_all()
    refreshed_shot = db_session.get(Shot, shot.id)
    assert refreshed_shot is not None
    assert refreshed_shot.active_attempt_id == attempt.id
    assert refreshed_shot.status == expected_shot_status


def test_review_non_active_attempt_does_not_change_parent_shot_status(
    api_client: TestClient,
    db_session,
):
    project = Project(name="Non Active Review Status Project")
    db_session.add(project)
    db_session.commit()

    shot = Shot(
        project_id=project.id,
        order=0,
        start_time=0.0,
        end_time=2.0,
        duration=2.0,
        status=ShotStatus.NEEDS_REVIEW.value,
    )
    db_session.add(shot)
    db_session.commit()

    active_attempt = Attempt(shot_id=shot.id, status=AttemptStatus.NEEDS_REVIEW.value)
    other_attempt = Attempt(shot_id=shot.id, status=AttemptStatus.NEEDS_REVIEW.value)
    db_session.add_all([active_attempt, other_attempt])
    db_session.commit()
    shot.active_attempt_id = active_attempt.id
    db_session.commit()

    response = api_client.post(
        f"/api/shots/{shot.id}/attempts/{other_attempt.id}/review",
        json={"status": AttemptStatus.REJECTED.value},
    )

    assert response.status_code == 200
    db_session.expire_all()
    refreshed_shot = db_session.get(Shot, shot.id)
    assert refreshed_shot is not None
    assert refreshed_shot.active_attempt_id == active_attempt.id
    assert refreshed_shot.status == ShotStatus.NEEDS_REVIEW.value


def test_delete_inactive_attempt_keeps_active_attempt(api_client: TestClient, db_session):
    project = Project(name="Delete Inactive Attempt Project")
    db_session.add(project)
    db_session.commit()

    shot = Shot(
        project_id=project.id,
        order=0,
        start_time=0.0,
        end_time=2.0,
        duration=2.0,
        status=ShotStatus.NEEDS_REVIEW.value,
    )
    db_session.add(shot)
    db_session.commit()

    active_attempt = Attempt(shot_id=shot.id, status=AttemptStatus.NEEDS_REVIEW.value)
    stale_attempt = Attempt(shot_id=shot.id, status=AttemptStatus.REJECTED.value)
    db_session.add_all([active_attempt, stale_attempt])
    db_session.commit()
    shot.active_attempt_id = active_attempt.id
    db_session.commit()
    active_attempt_id = active_attempt.id
    stale_attempt_id = stale_attempt.id

    response = api_client.delete(f"/api/shots/{shot.id}/attempts/{stale_attempt_id}")

    assert response.status_code == 204
    db_session.expire_all()
    assert db_session.get(Attempt, stale_attempt_id) is None
    db_session.refresh(shot)
    assert shot.active_attempt_id == active_attempt_id
    assert shot.status == ShotStatus.NEEDS_REVIEW.value


def test_delete_active_attempt_clears_active_attempt(api_client: TestClient, db_session):
    project = Project(name="Delete Active Attempt Project")
    db_session.add(project)
    db_session.commit()

    shot = Shot(
        project_id=project.id,
        order=0,
        start_time=0.0,
        end_time=2.0,
        duration=2.0,
        status=ShotStatus.NEEDS_REVIEW.value,
    )
    db_session.add(shot)
    db_session.commit()

    attempt = Attempt(shot_id=shot.id, status=AttemptStatus.NEEDS_REVIEW.value)
    db_session.add(attempt)
    db_session.commit()
    shot.active_attempt_id = attempt.id
    db_session.commit()
    attempt_id = attempt.id

    response = api_client.delete(f"/api/shots/{shot.id}/attempts/{attempt_id}")

    assert response.status_code == 204
    db_session.expire_all()
    assert db_session.get(Attempt, attempt_id) is None
    db_session.refresh(shot)
    assert shot.active_attempt_id is None
    assert shot.status == ShotStatus.NEEDS_INPUT.value


def test_delete_attempt_rejects_wrong_shot(api_client: TestClient, db_session):
    project = Project(name="Delete Wrong Shot Attempt Project")
    db_session.add(project)
    db_session.commit()

    first_shot = Shot(
        project_id=project.id,
        order=0,
        start_time=0.0,
        end_time=2.0,
        duration=2.0,
    )
    second_shot = Shot(
        project_id=project.id,
        order=1,
        start_time=2.0,
        end_time=4.0,
        duration=2.0,
    )
    db_session.add_all([first_shot, second_shot])
    db_session.commit()

    attempt = Attempt(shot_id=first_shot.id, status=AttemptStatus.NEEDS_INPUT.value)
    db_session.add(attempt)
    db_session.commit()

    response = api_client.delete(f"/api/shots/{second_shot.id}/attempts/{attempt.id}")

    assert response.status_code == 404
    assert db_session.get(Attempt, attempt.id) is not None
