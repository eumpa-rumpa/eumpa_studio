"""Workflow template and execution mode routes for eumpa_studio API."""

from __future__ import annotations

import datetime
import json
from pathlib import Path
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from eumpa_studio.db.session import get_session
from eumpa_studio.domain.models import ExecutionMode, WorkflowTemplate
from eumpa_studio.execution.workflow_patch import ValidationError, apply_mode

router = APIRouter()

DbSession = Annotated[Session, Depends(get_session)]

SKILL_LTX_WORKFLOW_PATH = (
    "/Users/songhaban/.codex/skills/comfy-ltx-lipsync-runner/assets/workflows/"
    "default_ltx2_ia2v_lipsync.json"
)
SKILL_LTX_NODE_BINDINGS = {
    "image": {"node_id": "14", "field": "image"},
    "audio": {"node_id": "40", "field": "audio"},
    "start_time": {"node_id": "40", "field": "start_time"},
    "duration": {"node_id": "40", "field": "duration"},
    "prompt_en": {"node_id": "11", "field": "text"},
    "seed": {"node_id": "1", "field": "noise_seed"},
    "output_prefix": {"node_id": "7", "field": "filename_prefix"},
}


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class WorkflowTemplateRead(BaseModel):
    id: str
    name: str
    json_path: str
    file_hash: str | None
    version: str | None
    compatibility_notes: str | None
    is_available: bool
    validation_error: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


class WorkflowTemplateCreate(BaseModel):
    name: str
    json_path: str
    file_hash: Optional[str] = None
    version: Optional[str] = None
    compatibility_notes: Optional[str] = None


class ExecutionModeRead(BaseModel):
    id: str
    workflow_template_id: str
    name: str
    required_inputs: str | None
    optional_inputs: str | None
    node_bindings: str | None
    validation_rules: str | None
    exposed_params: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


class ExecutionModeCreate(BaseModel):
    name: str
    required_inputs: Optional[str] = "[]"
    optional_inputs: Optional[str] = "[]"
    node_bindings: Optional[str] = "{}"
    validation_rules: Optional[str] = "{}"
    exposed_params: Optional[str] = "{}"


class PatchRequest(BaseModel):
    workflow_json: str
    mode_id: str
    inputs: dict[str, Any]


class PatchResponse(BaseModel):
    patched_workflow: str


class SkillWorkflowBootstrapRead(BaseModel):
    template: WorkflowTemplateRead
    mode: ExecutionModeRead


def _workflow_template_validation_error(json_path: str) -> str | None:
    workflow_path = Path(json_path)
    if not workflow_path.is_file():
        return f"Workflow template file not found: {json_path}"

    try:
        workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return f"Workflow template JSON is invalid: {json_path}"

    if not isinstance(workflow, dict) or not workflow:
        return "Workflow template JSON must be a non-empty object"

    return None


def _read_workflow_template(template: WorkflowTemplate) -> WorkflowTemplateRead:
    validation_error = _workflow_template_validation_error(template.json_path)
    return WorkflowTemplateRead(
        id=template.id,
        name=template.name,
        json_path=template.json_path,
        file_hash=template.file_hash,
        version=template.version,
        compatibility_notes=template.compatibility_notes,
        is_available=validation_error is None,
        validation_error=validation_error,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


# ---------------------------------------------------------------------------
# WorkflowTemplate routes
# ---------------------------------------------------------------------------


@router.post("/workflows/templates", response_model=WorkflowTemplateRead, status_code=201)
def create_workflow_template(
    body: WorkflowTemplateCreate,
    db: DbSession,
) -> WorkflowTemplateRead:
    """Create a new workflow template."""
    validation_error = _workflow_template_validation_error(body.json_path)
    if validation_error is not None:
        raise HTTPException(status_code=422, detail=validation_error)

    template = WorkflowTemplate(
        name=body.name,
        json_path=body.json_path,
        file_hash=body.file_hash,
        version=body.version,
        compatibility_notes=body.compatibility_notes,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return _read_workflow_template(template)


@router.get("/workflows/templates", response_model=list[WorkflowTemplateRead])
def list_workflow_templates(db: DbSession) -> list[WorkflowTemplateRead]:
    """List all workflow templates."""
    templates = db.scalars(
        select(WorkflowTemplate).order_by(WorkflowTemplate.created_at, WorkflowTemplate.id)
    )
    return [_read_workflow_template(template) for template in templates]


@router.get("/workflows/templates/{template_id}", response_model=WorkflowTemplateRead)
def get_workflow_template(template_id: str, db: DbSession) -> WorkflowTemplateRead:
    """Get a workflow template by ID."""
    template = db.get(WorkflowTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="WorkflowTemplate not found")
    return _read_workflow_template(template)


@router.post(
    "/workflows/skill-defaults/ltx-lipsync",
    response_model=SkillWorkflowBootstrapRead,
    status_code=201,
)
def bootstrap_ltx_lipsync_workflow(db: DbSession) -> SkillWorkflowBootstrapRead:
    """Register the bundled ComfyUI/LTX lip-sync skill workflow and mode."""
    validation_error = _workflow_template_validation_error(SKILL_LTX_WORKFLOW_PATH)
    if validation_error is not None:
        raise HTTPException(status_code=422, detail=validation_error)

    template = db.scalars(
        select(WorkflowTemplate).where(WorkflowTemplate.json_path == SKILL_LTX_WORKFLOW_PATH)
    ).first()
    if template is None:
        template = WorkflowTemplate(
            name="Skill default LTX lip-sync",
            json_path=SKILL_LTX_WORKFLOW_PATH,
            version="skill-default",
            compatibility_notes="Bundled by comfy-ltx-lipsync-runner skill.",
        )
        db.add(template)
        db.commit()
        db.refresh(template)

    mode = db.scalars(
        select(ExecutionMode)
        .where(ExecutionMode.workflow_template_id == template.id)
        .where(ExecutionMode.name == "Skill LTX image audio prompt")
    ).first()
    if mode is None:
        mode = ExecutionMode(
            workflow_template_id=template.id,
            name="Skill LTX image audio prompt",
            required_inputs=json.dumps(
                ["image", "audio", "start_time", "duration", "prompt_en"]
            ),
            optional_inputs=json.dumps(["seed", "output_prefix"]),
            node_bindings=json.dumps(SKILL_LTX_NODE_BINDINGS),
            validation_rules="{}",
            exposed_params="{}",
        )
        db.add(mode)
        db.commit()
        db.refresh(mode)

    return SkillWorkflowBootstrapRead(
        template=_read_workflow_template(template),
        mode=ExecutionModeRead.model_validate(mode),
    )


# ---------------------------------------------------------------------------
# ExecutionMode routes
# ---------------------------------------------------------------------------


@router.post(
    "/workflows/templates/{template_id}/modes",
    response_model=ExecutionModeRead,
    status_code=201,
)
def create_execution_mode(
    template_id: str,
    body: ExecutionModeCreate,
    db: DbSession,
) -> ExecutionMode:
    """Create an execution mode for a workflow template."""
    template = db.get(WorkflowTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="WorkflowTemplate not found")

    mode = ExecutionMode(
        workflow_template_id=template_id,
        name=body.name,
        required_inputs=body.required_inputs,
        optional_inputs=body.optional_inputs,
        node_bindings=body.node_bindings,
        validation_rules=body.validation_rules,
        exposed_params=body.exposed_params,
    )
    db.add(mode)
    db.commit()
    db.refresh(mode)
    return mode


@router.get(
    "/workflows/templates/{template_id}/modes",
    response_model=list[ExecutionModeRead],
)
def list_execution_modes(template_id: str, db: DbSession) -> list[ExecutionMode]:
    """List execution modes for a workflow template."""
    template = db.get(WorkflowTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="WorkflowTemplate not found")
    return list(
        db.scalars(
            select(ExecutionMode)
            .where(ExecutionMode.workflow_template_id == template_id)
            .order_by(ExecutionMode.created_at, ExecutionMode.id)
        ).all()
    )


# ---------------------------------------------------------------------------
# Patch endpoint
# ---------------------------------------------------------------------------


@router.post("/workflows/patch", response_model=PatchResponse)
def patch_workflow_endpoint(body: PatchRequest, db: DbSession) -> PatchResponse:
    """Validate inputs against an execution mode and patch a ComfyUI workflow JSON."""
    mode = db.get(ExecutionMode, body.mode_id)
    if mode is None:
        raise HTTPException(status_code=404, detail="ExecutionMode not found")

    required_inputs: list[str] = json.loads(mode.required_inputs) if mode.required_inputs else []
    node_bindings: dict[str, Any] = json.loads(mode.node_bindings) if mode.node_bindings else {}

    try:
        patched = apply_mode(
            workflow_json=body.workflow_json,
            mode_required_inputs=required_inputs,
            mode_node_bindings=node_bindings,
            inputs=body.inputs,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return PatchResponse(patched_workflow=patched)
