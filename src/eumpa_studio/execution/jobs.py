"""Job runner interfaces for background execution."""

from typing import Protocol


class JobRunner(Protocol):
    """Callable that executes a queued job."""

    def __call__(self, job_type: str, target_entity_id: str | None) -> None:
        """Run a job by type for an optional target entity id."""


def unsupported_job_runner(job_type: str, target_entity_id: str | None) -> None:
    """Default runner used until concrete job handlers are wired in."""
    raise NotImplementedError(
        f"No job runner registered for job type {job_type!r} target {target_entity_id!r}"
    )

