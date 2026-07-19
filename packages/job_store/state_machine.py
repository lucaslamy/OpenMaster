"""Pure legal state transitions for retry-safe analysis jobs."""

from datetime import datetime
from typing import Any

from .models import AnalysisJob, JobStatus


class JobTransitionError(ValueError):
    """Raised when a caller attempts an illegal job lifecycle transition."""


def claim(job: AnalysisJob, worker_id: str, now: datetime) -> AnalysisJob:
    """Lease a queued or retry-ready job to one worker."""
    if not worker_id:
        raise JobTransitionError("A worker identifier is required")
    if job.status not in {JobStatus.QUEUED, JobStatus.RETRY_WAIT}:
        raise JobTransitionError("Only queued jobs can be claimed")
    return job.with_updates(
        status=JobStatus.RUNNING,
        attempt_count=job.attempt_count + 1,
        updated_at=now,
        lease_owner=worker_id,
        error_code=None,
        error_message=None,
    )


def succeed(job: AnalysisJob, worker_id: str, result: dict[str, Any], now: datetime) -> AnalysisJob:
    """Finish a worker-owned running job with a serialized analysis result."""
    _require_lease(job, worker_id)
    return job.with_updates(
        status=JobStatus.SUCCEEDED,
        updated_at=now,
        lease_owner=None,
        result=result,
        error_code=None,
        error_message=None,
    )


def fail(job: AnalysisJob, worker_id: str, code: str, message: str, now: datetime) -> AnalysisJob:
    """Finish or schedule retry for a worker-owned failed job."""
    _require_lease(job, worker_id)
    status = JobStatus.RETRY_WAIT if job.attempt_count < job.max_attempts else JobStatus.FAILED
    return job.with_updates(
        status=status,
        updated_at=now,
        lease_owner=None,
        error_code=code,
        error_message=message,
    )


def _require_lease(job: AnalysisJob, worker_id: str) -> None:
    """Ensure a stale or unrelated worker cannot alter job outcome."""
    if job.status != JobStatus.RUNNING or job.lease_owner != worker_id:
        raise JobTransitionError("Job is not leased by this worker")
