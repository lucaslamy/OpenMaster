"""Immutable job models independent of persistence and transport."""

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from typing import Any


class JobStatus(StrEnum):
    """The durable states supported by an analysis job."""

    QUEUED = "queued"
    RUNNING = "running"
    RETRY_WAIT = "retry_wait"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class AnalysisJob:
    """Persistent job state expressed without database implementation details."""

    id: str
    input_path: str
    status: JobStatus
    attempt_count: int
    max_attempts: int
    updated_at: datetime
    lease_owner: str | None = None
    result: dict[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None

    def with_updates(self, **changes: Any) -> "AnalysisJob":
        """Return a new job state while retaining immutable lifecycle records."""
        return replace(self, **changes)
