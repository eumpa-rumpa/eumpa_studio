"""Job runner interfaces for background execution."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from sqlalchemy.orm import Session

from eumpa_studio.execution.align import run_alignment_job
from eumpa_studio.execution.comfy_client import run_render_job


class JobRunner(Protocol):
    """Callable that executes a queued job."""

    def __call__(self, job_type: str, target_entity_id: str | None) -> None:
        """Run a job by type for an optional target entity id."""


def unsupported_job_runner(job_type: str, target_entity_id: str | None) -> None:
    """Default runner used until concrete job handlers are wired in."""
    raise NotImplementedError(
        f"No job runner registered for job type {job_type!r} target {target_entity_id!r}"
    )


class AppJobRunner:
    """Dispatch queued jobs to concrete application runners."""

    def __init__(
        self,
        session_factory: Callable[[], Session],
        settings: object,
        align_runner: Callable[[Session, str, object], None] = run_alignment_job,
        render_runner: Callable[[Session, str, str, Path], None] = run_render_job,
    ) -> None:
        self.session_factory = session_factory
        self.settings = settings
        self.align_runner = align_runner
        self.render_runner = render_runner

    def __call__(self, job_type: str, target_entity_id: str | None) -> None:
        if not target_entity_id:
            raise ValueError(f"Job type {job_type!r} requires a target entity id")

        with self.session_factory() as session:
            if job_type == "align":
                self.align_runner(session, target_entity_id, self.settings)
                session.commit()
                return

            if job_type in {"render", "render_attempt"}:
                comfyui_url = str(getattr(self.settings, "comfyui_url"))
                data_root = Path(getattr(self.settings, "data_root", "data"))
                self.render_runner(session, target_entity_id, comfyui_url, data_root)
                session.commit()
                return

        raise NotImplementedError(
            f"No job runner registered for job type {job_type!r} target {target_entity_id!r}"
        )
