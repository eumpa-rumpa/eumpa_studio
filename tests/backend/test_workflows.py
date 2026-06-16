"""Tests for workflow template and execution mode routes."""

from __future__ import annotations

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
def session_factory(test_settings):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session_ = sessionmaker(bind=engine)
    yield Session_
    engine.dispose()


@pytest.fixture()
def api_client(session_factory, test_settings):
    def override_get_session():
        with session_factory() as session:
            yield session

    def override_get_settings():
        return test_settings

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_settings_dep] = override_get_settings
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_create_execution_mode_defaults_optional_json_fields(api_client: TestClient, tmp_path):
    workflow_path = tmp_path / "workflow.json"
    workflow_path.write_text('{"1": {"class_type": "TestNode", "inputs": {}}}', encoding="utf-8")

    template_response = api_client.post(
        "/api/workflows/templates",
        json={"name": "LTX", "json_path": str(workflow_path)},
    )
    assert template_response.status_code == 201
    template_body = template_response.json()
    template_id = template_body["id"]
    assert template_body["is_available"] is True
    assert template_body["validation_error"] is None

    mode_response = api_client.post(
        f"/api/workflows/templates/{template_id}/modes",
        json={
            "name": "Image prompt",
            "required_inputs": '["image", "prompt_en"]',
            "node_bindings": "{}",
        },
    )

    assert mode_response.status_code == 201
    body = mode_response.json()
    assert body["optional_inputs"] == "[]"
    assert body["validation_rules"] == "{}"
    assert body["exposed_params"] == "{}"


def test_create_workflow_template_rejects_missing_file(api_client: TestClient):
    template_response = api_client.post(
        "/api/workflows/templates",
        json={"name": "Missing", "json_path": "/tmp/does-not-exist-eumpa-workflow.json"},
    )

    assert template_response.status_code == 422
    assert "Workflow template file not found" in template_response.json()["detail"]


def test_bootstrap_ltx_lipsync_skill_workflow_is_idempotent(
    api_client: TestClient,
    test_settings,
):
    first_response = api_client.post("/api/workflows/skill-defaults/ltx-lipsync")
    second_response = api_client.post("/api/workflows/skill-defaults/ltx-lipsync")

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    first = first_response.json()
    second = second_response.json()
    assert first["template"]["id"] == second["template"]["id"]
    assert first["mode"]["id"] == second["mode"]["id"]
    assert first["template"]["is_available"] is True
    assert first["template"]["json_path"] == second["template"]["json_path"]
    assert str(test_settings.data_root) in first["template"]["json_path"]
    assert ".codex/skills" not in first["template"]["json_path"]
    assert first["mode"]["required_inputs"] == (
        '["image", "audio", "start_time", "duration", "prompt_en"]'
    )
    assert '"node_id": "14"' in first["mode"]["node_bindings"]
    assert (test_settings.data_root / "workflows" / "skill-defaults" / "default_ltx2_ia2v_lipsync.json").is_file()
