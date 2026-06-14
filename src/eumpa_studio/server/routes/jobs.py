"""Jobs route for eumpa_studio API."""

from __future__ import annotations

import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from eumpa_studio.db.session import get_session
from eumpa_studio.domain.models import Job
from eumpa_studio.domain.statuses import JobStatus

router = APIRouter()


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


@router.post("/jobs", response_model=JobRead, status_code=201)
def enqueue_job(body: JobCreate, db: DbSession) -> Job:
    job = Job(
        type=body.type,
        target_entity_type=body.target_entity_type,
        target_entity_id=body.target_entity_id,
        status=JobStatus.PENDING.value,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("/jobs", response_model=list[JobRead])
def list_jobs(db: DbSession) -> list[Job]:
    return list(db.scalars(select(Job).order_by(Job.created_at, Job.id)).all())


@router.get("/jobs/{job_id}", response_model=JobRead)
def get_job(job_id: str, db: DbSession) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
