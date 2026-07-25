"""Synchronous repository for durable analysis-job state."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Engine, create_engine, insert, select, update
from sqlalchemy.exc import IntegrityError

from .models import analysis_jobs


@dataclass(frozen=True, slots=True)
class AnalysisJobRecord:
    """JSON-safe state returned by the API and updated by workers."""

    id: str
    status: str
    object_name: str
    original_filename: str
    attempt_count: int
    result: dict[str, Any] | None = None
    error_code: str | None = None
    error_message: str | None = None


class AnalysisJobRepository:
    """Persist and retrieve analysis jobs using short SQLAlchemy transactions."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    @classmethod
    def from_environment(cls) -> AnalysisJobRepository:
        """Create a repository from the runtime database URL."""
        return cls(create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True))

    def create_or_get(
        self,
        *,
        job_id: str,
        idempotency_key: str,
        object_name: str,
        original_filename: str,
    ) -> tuple[AnalysisJobRecord, bool]:
        """Insert one queued job, returning the existing row on a key race."""
        existing = self.get_by_idempotency_key(idempotency_key)
        if existing is not None:
            return existing, False
        now = datetime.now(UTC)
        try:
            with self._engine.begin() as connection:
                connection.execute(
                    insert(analysis_jobs).values(
                        id=job_id,
                        idempotency_key=idempotency_key,
                        status="queued",
                        object_name=object_name,
                        original_filename=original_filename,
                        attempt_count=0,
                        updated_at=now,
                    )
                )
        except IntegrityError:
            raced = self.get_by_idempotency_key(idempotency_key)
            if raced is None:
                raise
            return raced, False
        created = self.get(job_id)
        if created is None:  # pragma: no cover - defensive database invariant
            raise RuntimeError("Analysis job disappeared after insertion")
        return created, True

    def get(self, job_id: str) -> AnalysisJobRecord | None:
        """Return one job by UUID."""
        with self._engine.connect() as connection:
            row = (
                connection.execute(select(analysis_jobs).where(analysis_jobs.c.id == job_id))
                .mappings()
                .one_or_none()
            )
        return _record(row) if row is not None else None

    def get_by_idempotency_key(self, key: str) -> AnalysisJobRecord | None:
        """Return the job previously created with an idempotency key."""
        with self._engine.connect() as connection:
            row = (
                connection.execute(
                    select(analysis_jobs).where(analysis_jobs.c.idempotency_key == key)
                )
                .mappings()
                .one_or_none()
            )
        return _record(row) if row is not None else None

    def mark_running(self, job_id: str) -> None:
        """Record worker ownership without exposing leases through the HTTP API."""
        self._update(
            job_id,
            status="running",
            attempt_count=analysis_jobs.c.attempt_count + 1,
            error_code=None,
            error_message=None,
        )

    def mark_succeeded(self, job_id: str, result: dict[str, Any]) -> None:
        """Persist a JSON-safe analysis result."""
        self._update(job_id, status="succeeded", result=result)

    def mark_failed(self, job_id: str, code: str, message: str) -> None:
        """Persist a bounded public failure description."""
        self._update(
            job_id,
            status="failed",
            error_code=code[:64],
            error_message=message[:2000],
        )

    def _update(self, job_id: str, **values: Any) -> None:
        values["updated_at"] = datetime.now(UTC)
        with self._engine.begin() as connection:
            result = connection.execute(
                update(analysis_jobs).where(analysis_jobs.c.id == job_id).values(**values)
            )
            if result.rowcount != 1:
                raise KeyError(f"Unknown analysis job {job_id}")


def _record(row: Any) -> AnalysisJobRecord:
    object_name = row["object_name"]
    original_filename = row["original_filename"]
    if not isinstance(object_name, str) or not isinstance(original_filename, str):
        raise ValueError("Legacy analysis job does not contain an upload contract")
    return AnalysisJobRecord(
        id=row["id"],
        status=row["status"],
        object_name=object_name,
        original_filename=original_filename,
        attempt_count=row["attempt_count"],
        result=row["result"],
        error_code=row["error_code"],
        error_message=row["error_message"],
    )
