"""Projects route for eumpa_studio API."""

from __future__ import annotations

import datetime
import mimetypes
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from eumpa_studio.config import Settings
from eumpa_studio.db.session import get_session
from eumpa_studio.domain.models import Project
from eumpa_studio.server.deps import get_settings_dep
from eumpa_studio.storage.paths import ensure_project_dirs, save_upload

router = APIRouter()


class ProjectRead(BaseModel):
    id: str
    name: str
    audio_storage_backend: Optional[str]
    audio_relative_path: Optional[str]
    lyrics_text: Optional[str]
    lyrics_storage_backend: Optional[str]
    lyrics_relative_path: Optional[str]
    visual_bible_text: Optional[str]
    visual_bible_storage_backend: Optional[str]
    visual_bible_relative_path: Optional[str]
    default_comfyui_server: Optional[str]
    created_at: datetime.datetime
    updated_at: datetime.datetime

    model_config = {"from_attributes": True}


DbSession = Annotated[Session, Depends(get_session)]
AppSettings = Annotated[Settings, Depends(get_settings_dep)]


@router.post("/projects", response_model=ProjectRead, status_code=201)
def create_project(
    db: DbSession,
    settings: AppSettings,
    name: Annotated[str, Form()],
    lyrics_text: Annotated[Optional[str], Form()] = None,
    visual_bible_text: Annotated[Optional[str], Form()] = None,
    audio: Optional[UploadFile] = None,
    lyrics_file: Optional[UploadFile] = None,
    visual_bible_file: Optional[UploadFile] = None,
) -> Project:
    """Create a new project with optional file uploads."""
    project = Project(name=name)
    db.add(project)
    db.flush()  # assign id before creating dirs

    project_id = project.id
    inputs_dir = ensure_project_dirs(settings.data_root, project_id)

    if audio is not None and audio.filename:
        backend, rel_path = save_upload(audio, inputs_dir, settings.data_root)
        project.audio_storage_backend = backend
        project.audio_relative_path = rel_path

    if lyrics_text is not None:
        project.lyrics_text = lyrics_text

    if lyrics_file is not None and lyrics_file.filename:
        backend, rel_path = save_upload(lyrics_file, inputs_dir, settings.data_root)
        project.lyrics_storage_backend = backend
        project.lyrics_relative_path = rel_path

    if visual_bible_text is not None:
        project.visual_bible_text = visual_bible_text

    if visual_bible_file is not None and visual_bible_file.filename:
        backend, rel_path = save_upload(visual_bible_file, inputs_dir, settings.data_root)
        project.visual_bible_storage_backend = backend
        project.visual_bible_relative_path = rel_path

    db.commit()
    db.refresh(project)
    return project


@router.get("/projects", response_model=list[ProjectRead])
def list_projects(db: DbSession) -> list[Project]:
    """List all projects ordered by creation time."""
    return list(db.scalars(select(Project).order_by(Project.created_at, Project.id)).all())


@router.get("/projects/{project_id}", response_model=ProjectRead)
def get_project(project_id: str, db: DbSession) -> Project:
    """Get a single project by ID."""
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/projects/{project_id}/audio")
def get_project_audio(project_id: str, db: DbSession, settings: AppSettings) -> FileResponse:
    """Serve the source audio file for a project."""
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.audio_relative_path:
        raise HTTPException(status_code=404, detail="Project audio not found")

    audio_path = settings.data_root / project.audio_relative_path
    if not audio_path.is_file():
        raise HTTPException(status_code=404, detail="Project audio not found")

    media_type = mimetypes.guess_type(audio_path.name)[0] or "application/octet-stream"
    return FileResponse(str(audio_path), media_type=media_type)
