"""Tests for workflow template and execution mode routes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from eumpa_studio.db.base import Base
from eumpa_studio.db.session import get_session
from eumpa_studio.server.app import app


@pytest.fixture()
def session_factory():
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
def api_client(session_factory):
    def override_get_session():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
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


def test_bootstrap_ltx_lipsync_skill_workflow_is_idempotent(api_client: TestClient):
    first_response = api_client.post("/api/workflows/skill-defaults/ltx-lipsync")
    second_response = api_client.post("/api/workflows/skill-defaults/ltx-lipsync")

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    first = first_response.json()
    second = second_response.json()
    assert first["template"]["id"] == second["template"]["id"]
    assert first["mode"]["id"] == second["mode"]["id"]
    assert first["template"]["is_available"] is True
    assert first["mode"]["required_inputs"] == (
        '["image", "audio", "start_time", "duration", "prompt_en"]'
    )
    assert '"node_id": "14"' in first["mode"]["node_bindings"]
