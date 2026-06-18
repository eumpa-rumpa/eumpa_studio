"""SQLAlchemy ORM models for eumpa_studio MVP entities."""

import datetime
import uuid
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from eumpa_studio.db.base import Base
from eumpa_studio.domain.statuses import AttemptStatus, JobStatus, ShotStatus


def _uuid() -> str:
    return str(uuid.uuid4())


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)

    # Audio file reference (optional)
    audio_storage_backend: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    audio_relative_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Lyrics (optional)
    lyrics_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    lyrics_storage_backend: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    lyrics_relative_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Visual bible (optional)
    visual_bible_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    visual_bible_storage_backend: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    visual_bible_relative_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    default_comfyui_server: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    shots: Mapped[list["Shot"]] = relationship("Shot", back_populates="project")
    assets: Mapped[list["Asset"]] = relationship("Asset", back_populates="project")


class Shot(Base):
    __tablename__ = "shots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False
    )
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[float] = mapped_column(Float, nullable=False)
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    duration: Mapped[float] = mapped_column(Float, nullable=False)
    speaker: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    lyrics_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    shot_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String, nullable=False, default=ShotStatus.NEEDS_INPUT.value
    )
    active_attempt_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("attempts.id", use_alter=True, name="fk_shot_active_attempt"),
        nullable=True,
    )

    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="shots")
    attempts: Mapped[list["Attempt"]] = relationship(
        "Attempt",
        back_populates="shot",
        foreign_keys="Attempt.shot_id",
    )
    active_attempt: Mapped[Optional["Attempt"]] = relationship(
        "Attempt",
        foreign_keys=[active_attempt_id],
        primaryjoin="Shot.active_attempt_id == Attempt.id",
        uselist=False,
    )


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    shot_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("shots.id"), nullable=False
    )
    parent_attempt_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("attempts.id"), nullable=True
    )

    # Image file reference (optional)
    image_storage_backend: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    image_relative_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # End image (optional)
    end_image_storage_backend: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    end_image_relative_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    # Input video (optional)
    input_video_storage_backend: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    input_video_relative_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    shot_note_snapshot: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prompt_ko: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prompt_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    workflow_template_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("workflow_templates.id"), nullable=True
    )
    execution_mode_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("execution_modes.id"), nullable=True
    )

    param_overrides: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    seed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    workflow_snapshot: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    comfyui_prompt_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    output_metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    review_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String, nullable=False, default=AttemptStatus.NEEDS_INPUT.value
    )

    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    shot: Mapped["Shot"] = relationship(
        "Shot",
        back_populates="attempts",
        foreign_keys=[shot_id],
    )
    workflow_template: Mapped[Optional["WorkflowTemplate"]] = relationship(
        "WorkflowTemplate", back_populates="attempts"
    )
    execution_mode: Mapped[Optional["ExecutionMode"]] = relationship(
        "ExecutionMode", back_populates="attempts"
    )
    children: Mapped[list["Attempt"]] = relationship(
        "Attempt", back_populates="parent", foreign_keys=[parent_attempt_id]
    )
    parent: Mapped[Optional["Attempt"]] = relationship(
        "Attempt", back_populates="children", foreign_keys=[parent_attempt_id], remote_side=[id]
    )


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    storage_backend: Mapped[str] = mapped_column(String, nullable=False)
    relative_path: Mapped[str] = mapped_column(String, nullable=False)
    mime_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="assets")


class StudioSetting(Base):
    __tablename__ = "studio_settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )


class WorkflowTemplate(Base):
    __tablename__ = "workflow_templates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, nullable=False)
    json_path: Mapped[str] = mapped_column(String, nullable=False)
    file_hash: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    version: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    compatibility_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    execution_modes: Mapped[list["ExecutionMode"]] = relationship(
        "ExecutionMode", back_populates="workflow_template"
    )
    attempts: Mapped[list["Attempt"]] = relationship(
        "Attempt", back_populates="workflow_template"
    )


class ExecutionMode(Base):
    __tablename__ = "execution_modes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    workflow_template_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workflow_templates.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    required_inputs: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    optional_inputs: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    node_bindings: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    validation_rules: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    exposed_params: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # Relationships
    workflow_template: Mapped["WorkflowTemplate"] = relationship(
        "WorkflowTemplate", back_populates="execution_modes"
    )
    attempts: Mapped[list["Attempt"]] = relationship(
        "Attempt", back_populates="execution_mode"
    )


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    type: Mapped[str] = mapped_column(String, nullable=False)
    target_entity_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    target_entity_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(
        String, nullable=False, default=JobStatus.PENDING.value
    )
    logs: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )
    started_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
