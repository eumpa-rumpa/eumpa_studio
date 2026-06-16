"""Jobs route for eumpa_studio API."""

from __future__ import annotations

import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from eumpa_studio.db.session import get_session
from eumpa_studio.domain.models import Attempt, Job
from eumpa_studio.domain.statuses import JobStatus

router = APIRouter()

# Known job types accepted by the API.  Extend this set as new job types are
# implemented.  The special value ``"render_attempt"`` is kept for backward
# compatibility with existing tests and integrations.
KNOWN_JOB_TYPES: frozenset[str] = frozenset(
    {"align", "prompt", "render", "render_attempt"}
)


class JobCreate(BaseModel):
    type: str
    target_entity_type: str | None = None
    target_entity_id: str | None = None


class JobRead(BaseModel):
    id: str
    type: str
    target_entity_type: str | None
    target_entity_id: str | None
    status: str
    logs: str | None
    error: str | None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    started_at: datetime.datetime | None
    finished_at: datetime.datetime | None

    model_config = {"from_attributes": True}


DbSession = Annotated[Session, Depends(get_session)]


def _create_job(db: Session, job_type: str, target_entity_type: str | None, target_entity_id: str | None) -> Job:
    """Persist a new Job row and return it with a refreshed ID."""
    job = Job(
        type=job_type,
        target_entity_type=target_entity_type,
        target_entity_id=target_entity_id,
        status=JobStatus.PENDING.value,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.post("/jobs", response_model=JobRead, status_code=201)
def enqueue_job(body: JobCreate, db: DbSession) -> Job:
    if body.type not in KNOWN_JOB_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown job type {body.type!r}. Accepted types: {sorted(KNOWN_JOB_TYPES)}",
        )
    return _create_job(db, body.type, body.target_entity_type, body.target_entity_id)


@router.get("/jobs", response_model=list[JobRead])
def list_jobs(db: DbSession) -> list[Job]:
    return list(db.scalars(select(Job).order_by(Job.created_at, Job.id)).all())


@router.get("/jobs/{job_id}", response_model=JobRead)
def get_job(job_id: str, db: DbSession) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/projects/{project_id}/align", response_model=JobRead, status_code=201)
def enqueue_alignment_job(project_id: str, db: DbSession) -> Job:
    """Create an alignment job for the given project.

    Returns 201 + :class:`JobRead` with ``type="align"``.
    """
    return _create_job(db, "align", "project", project_id)


@router.post(
    "/shots/{shot_id}/attempts/{attempt_id}/render",
    response_model=JobRead,
    status_code=201,
)
def enqueue_render_job(shot_id: str, attempt_id: str, db: DbSession) -> Job:
    """Create a render job for a configured shot attempt."""
    attempt = db.get(Attempt, attempt_id)
    if attempt is None or attempt.shot_id != shot_id:
        raise HTTPException(status_code=404, detail="Attempt not found")
    if not attempt.workflow_template_id or not attempt.execution_mode_id:
        raise HTTPException(
            status_code=422,
            detail="Select a workflow template and execution mode before rendering",
        )
    return _create_job(db, "render", "attempt", attempt_id)
