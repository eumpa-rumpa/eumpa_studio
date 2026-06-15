"""Single-worker loop for processing DB-backed jobs."""

from __future__ import annotations

import datetime
import threading
from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from eumpa_studio.domain.models import Job
from eumpa_studio.domain.statuses import JobStatus
from eumpa_studio.execution.jobs import JobRunner, unsupported_job_runner


SessionFactory = Callable[[], Session]


def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC).replace(tzinfo=None)


class WorkerLoop:
    """Poll the database and execute one pending job at a time."""

    def __init__(
        self,
        session_factory: SessionFactory,
        runner: JobRunner = unsupported_job_runner,
        poll_interval_seconds: float = 1.0,
    ) -> None:
        self.session_factory = session_factory
        self.runner = runner
        self.poll_interval_seconds = poll_interval_seconds

    def run_once(self) -> bool:
        """Process the oldest pending job, returning False when the queue is idle."""
        with self.session_factory() as session:
            job = self._next_pending_job(session)
            if job is None:
                return False

            job.status = JobStatus.RUNNING.value
            job.started_at = _utcnow()
            job.finished_at = None
            job.error = None
            session.commit()

            job_id = job.id
            job_type = job.type
            target_entity_id = job.target_entity_id

        try:
            self.runner(job_type, target_entity_id)
        except Exception as exc:
            self._mark_finished(job_id, JobStatus.FAILED, str(exc) or exc.__class__.__name__)
            return True

        self._mark_finished(job_id, JobStatus.DONE, None)
        return True

    def run_forever(self, stop_event: threading.Event | None = None) -> None:
        """Run jobs until the optional stop event is set."""
        stop_event = stop_event or threading.Event()
        while not stop_event.is_set():
            processed = self.run_once()
            if not processed:
                stop_event.wait(self.poll_interval_seconds)

    def start_in_thread(
        self,
        stop_event: threading.Event | None = None,
        daemon: bool = True,
    ) -> threading.Thread:
        """Start the worker loop in a background thread."""
        thread = threading.Thread(
            target=self.run_forever,
            kwargs={"stop_event": stop_event},
            daemon=daemon,
            name="eumpa-studio-worker",
        )
        thread.start()
        return thread

    def _next_pending_job(self, session: Session) -> Job | None:
        return session.scalars(
            select(Job)
            .where(Job.status == JobStatus.PENDING.value)
            .order_by(Job.created_at, Job.id)
            .limit(1)
        ).first()

    def _mark_finished(
        self,
        job_id: str,
        status: JobStatus,
        error: str | None,
    ) -> None:
        with self.session_factory() as session:
            job = session.get(Job, job_id)
            if job is None:
                return
            job.status = status.value
            job.finished_at = _utcnow()
            job.error = error
            session.commit()
