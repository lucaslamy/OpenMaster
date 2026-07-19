"""Unit tests for the retry-safe analysis job lifecycle."""

from datetime import UTC, datetime

import pytest

from packages.job_store import AnalysisJob, JobStatus, JobTransitionError, claim, fail, succeed


def _job(attempt_count: int = 0, max_attempts: int = 2) -> AnalysisJob:
    return AnalysisJob(
        "job-1", "/audio.wav", JobStatus.QUEUED, attempt_count, max_attempts, datetime.now(UTC)
    )


def test_claim_and_succeed_require_the_owning_worker() -> None:
    now = datetime.now(UTC)
    running = claim(_job(), "worker-a", now)

    succeeded = succeed(running, "worker-a", {"lufs": -14.0}, now)

    assert succeeded.status == JobStatus.SUCCEEDED
    assert succeeded.result == {"lufs": -14.0}
    with pytest.raises(JobTransitionError):
        succeed(running, "worker-b", {}, now)


def test_failure_retries_until_attempt_budget_is_exhausted() -> None:
    now = datetime.now(UTC)
    retrying = fail(claim(_job(), "worker-a", now), "worker-a", "internal", "retry", now)
    terminal = fail(claim(retrying, "worker-b", now), "worker-b", "internal", "failed", now)

    assert retrying.status == JobStatus.RETRY_WAIT
    assert terminal.status == JobStatus.FAILED
