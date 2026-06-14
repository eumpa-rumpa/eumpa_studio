"""Tests for workflow_patch utilities and workflow/mode API routes."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from eumpa_studio.config import Settings
from eumpa_studio.db.base import Base
from eumpa_studio.db.session import get_session
from eumpa_studio.execution.workflow_patch import (
    ValidationError,
    apply_mode,
    patch_workflow,
    validate_inputs,
)
from eumpa_studio.server.app import app
from eumpa_studio.server.deps import get_settings_dep

# ---------------------------------------------------------------------------
# Unit tests for workflow_patch.py
# ---------------------------------------------------------------------------


def test_validate_inputs_passes_when_all_required_present():
    """No exception raised when all required keys are in provided dict."""
    validate_inputs(["prompt", "seed"], {"prompt": "hello", "seed": 42, "extra": "x"})


def test_validate_inputs_raises_on_missing():
    """ValidationError raised when a required key is absent."""
    with pytest.raises(ValidationError) as exc_info:
        validate_inputs(["prompt", "seed"], {"prompt": "hello"})
    assert "seed" in str(exc_info.value)


def test_patch_workflow_sets_node_field():
    """patch_workflow sets the correct field on the correct node."""
    workflow = {"5": {"inputs": {"text": "old value", "width": 512}}}
    bindings = {"prompt": {"node_id": "5", "field": "text"}}
    result = patch_workflow(workflow, bindings, {"prompt": "new value"})
    assert result["5"]["inputs"]["text"] == "new value"


def test_patch_workflow_ignores_unknown_binding_key():
    """Binding keys not present in inputs are silently skipped."""
    workflow = {"5": {"inputs": {"text": "unchanged"}}}
    bindings = {"missing_key": {"node_id": "5", "field": "text"}}
    result = patch_workflow(workflow, bindings, {})
    assert result["5"]["inputs"]["text"] == "unchanged"


def test_patch_workflow_does_not_mutate_original():
    """patch_workflow returns a deep copy; the original dict is untouched."""
    workflow = {"5": {"inputs": {"text": "original"}}}
    bindings = {"prompt": {"node_id": "5", "field": "text"}}
    result = patch_workflow(workflow, bindings, {"prompt": "modified"})
    assert workflow["5"]["inputs"]["text"] == "original"
    assert result["5"]["inputs"]["text"] == "modified"


def test_apply_mode_validates_then_patches():
    """apply_mode validates required inputs and returns patched JSON string."""
    workflow = {"3": {"inputs": {"seed": 0, "prompt": ""}}}
    workflow_json = json.dumps(workflow)
    node_bindings = {
        "seed": {"node_id": "3", "field": "seed"},
        "prompt": {"node_id": "3", "field": "prompt"},
    }
    result_json = apply_mode(
        workflow_json=workflow_json,
        mode_required_inputs=["seed", "prompt"],
        mode_node_bindings=node_bindings,
        inputs={"seed": 999, "prompt": "a cat"},
    )
    result = json.loads(result_json)
    assert result["3"]["inputs"]["seed"] == 999
    assert result["3"]["inputs"]["prompt"] == "a cat"


# ---------------------------------------------------------------------------
# API tests
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


def test_create_workflow_template(api_client: TestClient):
    """POST /api/workflows/templates creates and returns a template."""
    response = api_client.post(
        "/api/workflows/templates",
        json={"name": "My Template", "json_path": "/workflows/my_template.json"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["name"] == "My Template"
    assert body["json_path"] == "/workflows/my_template.json"
    assert body["file_hash"] is None
    assert body["version"] is None
    assert body["compatibility_notes"] is None
    assert body["created_at"]
    assert body["updated_at"]


def test_create_execution_mode(api_client: TestClient):
    """POST /api/workflows/templates/{id}/modes creates an execution mode."""
    # First create a template
    tmpl_resp = api_client.post(
        "/api/workflows/templates",
        json={"name": "Template For Mode", "json_path": "/workflows/t.json"},
    )
    assert tmpl_resp.status_code == 201
    template_id = tmpl_resp.json()["id"]

    mode_resp = api_client.post(
        f"/api/workflows/templates/{template_id}/modes",
        json={
            "workflow_template_id": template_id,
            "name": "txt2img",
            "required_inputs": '["prompt"]',
            "node_bindings": '{"prompt": {"node_id": "6", "field": "text"}}',
        },
    )
    assert mode_resp.status_code == 201
    body = mode_resp.json()
    assert body["id"]
    assert body["workflow_template_id"] == template_id
    assert body["name"] == "txt2img"
    assert body["required_inputs"] == '["prompt"]'


def test_list_modes_for_template(api_client: TestClient):
    """GET /api/workflows/templates/{id}/modes lists modes for a template."""
    tmpl_resp = api_client.post(
        "/api/workflows/templates",
        json={"name": "Template List Modes", "json_path": "/workflows/tl.json"},
    )
    template_id = tmpl_resp.json()["id"]

    api_client.post(
        f"/api/workflows/templates/{template_id}/modes",
        json={
            "workflow_template_id": template_id,
            "name": "mode_a",
            "required_inputs": "[]",
            "node_bindings": "{}",
        },
    )
    api_client.post(
        f"/api/workflows/templates/{template_id}/modes",
        json={
            "workflow_template_id": template_id,
            "name": "mode_b",
            "required_inputs": "[]",
            "node_bindings": "{}",
        },
    )

    list_resp = api_client.get(f"/api/workflows/templates/{template_id}/modes")
    assert list_resp.status_code == 200
    modes = list_resp.json()
    names = [m["name"] for m in modes]
    assert "mode_a" in names
    assert "mode_b" in names


def test_patch_endpoint_applies_mode(api_client: TestClient):
    """POST /api/workflows/patch applies the execution mode's bindings."""
    # Create template + mode
    tmpl_resp = api_client.post(
        "/api/workflows/templates",
        json={"name": "Patch Template", "json_path": "/workflows/p.json"},
    )
    template_id = tmpl_resp.json()["id"]

    mode_resp = api_client.post(
        f"/api/workflows/templates/{template_id}/modes",
        json={
            "workflow_template_id": template_id,
            "name": "txt2img",
            "required_inputs": '["prompt"]',
            "node_bindings": '{"prompt": {"node_id": "6", "field": "text"}}',
        },
    )
    mode_id = mode_resp.json()["id"]

    # Build a minimal workflow JSON
    workflow = {"6": {"inputs": {"text": "placeholder", "cfg": 7}}}
    workflow_json = json.dumps(workflow)

    patch_resp = api_client.post(
        "/api/workflows/patch",
        json={
            "workflow_json": workflow_json,
            "mode_id": mode_id,
            "inputs": {"prompt": "a sunset over mountains"},
        },
    )
    assert patch_resp.status_code == 200
    patched = json.loads(patch_resp.json()["patched_workflow"])
    assert patched["6"]["inputs"]["text"] == "a sunset over mountains"
