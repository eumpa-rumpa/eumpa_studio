"""Tests for prompt-generation routes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from eumpa_studio.config import Settings
from eumpa_studio.db.base import Base
from eumpa_studio.db.session import get_session
from eumpa_studio.domain.models import Attempt, Project, Shot
from eumpa_studio.execution.codex_prompt import PromptResult
from eumpa_studio.server.app import app
from eumpa_studio.server.deps import get_db, get_settings_dep
from eumpa_studio.server.routes import prompts as prompt_routes


@pytest.fixture()
def test_settings(tmp_path):
    return Settings(
        data_root=tmp_path / "data",
        database_url="sqlite:///:memory:",
        codex_cli_path="codex",
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
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_settings_dep] = override_get_settings
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture()
def db_session(db_engine):
    Session_ = sessionmaker(bind=db_engine)
    with Session_() as session:
        yield session


def test_generate_prompt_passes_attempt_note_system_prompt_and_image_roles(
    api_client: TestClient,
    db_session,
    test_settings,
    monkeypatch,
):
    captured = {}
    project = Project(name="Prompt Route Project", visual_bible_text="neon stage")
    db_session.add(project)
    db_session.commit()

    shot = Shot(
        project_id=project.id,
        order=0,
        start_time=1.0,
        end_time=3.0,
        duration=2.0,
        speaker="rapper",
        lyrics_text="line one",
        shot_note="shot-level note",
    )
    db_session.add(shot)
    db_session.commit()

    attempt = Attempt(
        shot_id=shot.id,
        image_storage_backend="local",
        image_relative_path="projects/project-1/assets/start.png",
        end_image_storage_backend="local",
        end_image_relative_path="projects/project-1/assets/end.png",
        shot_note_snapshot="attempt note",
        prompt_en="previous prompt",
    )
    db_session.add(attempt)
    db_session.commit()

    def fake_run_codex_prompt(ctx, codex_cli_path):
        captured["ctx"] = ctx
        captured["codex_cli_path"] = codex_cli_path
        return PromptResult(
            image_observations="start and end are coherent",
            motion_camera_plan="push in",
            prompt_ko="생성된 한국어 프롬프트",
            prompt_en="Generated English prompt",
            negative_rules=None,
            rationale=None,
        )

    monkeypatch.setattr(prompt_routes, "run_codex_prompt", fake_run_codex_prompt)

    response = api_client.post(
        "/api/prompts/generate",
        json={"attempt_id": attempt.id, "system_prompt": "Custom LTX direction"},
    )

    assert response.status_code == 200
    assert response.json()["prompt_en"] == "Generated English prompt"
    ctx = captured["ctx"]
    assert ctx.shot_note == "attempt note"
    assert ctx.system_prompt == "Custom LTX direction"
    assert ctx.image_path == str(
        test_settings.data_root / "projects/project-1/assets/start.png",
    )
    assert ctx.end_image_path == str(
        test_settings.data_root / "projects/project-1/assets/end.png",
    )
    assert captured["codex_cli_path"] == "codex"
