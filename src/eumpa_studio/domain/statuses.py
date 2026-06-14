"""Status enums for eumpa_studio domain entities."""

import enum


class ShotStatus(str, enum.Enum):
    NEEDS_INPUT = "Needs Input"
    READY = "Ready"
    QUEUED = "Queued"
    RENDERING = "Rendering"
    NEEDS_REVIEW = "Needs Review"
    SELECTED = "Selected"
    REDO = "Redo"
    REJECTED = "Rejected"
    FAILED = "Failed"


class AttemptStatus(str, enum.Enum):
    NEEDS_INPUT = "Needs Input"
    READY = "Ready"
    QUEUED = "Queued"
    RENDERING = "Rendering"
    NEEDS_REVIEW = "Needs Review"
    SELECTED = "Selected"
    REDO = "Redo"
    REJECTED = "Rejected"
    FAILED = "Failed"


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
