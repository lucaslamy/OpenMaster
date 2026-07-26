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
    recommendation: dict[str, Any] | None = None
    mastering_result: dict[str, Any] | None = None
    output_object_name: str | None = None
    initial_output_object_name: str | None = None
    parent_job_id: str | None = None
    interactive_settings: dict[str, Any] | None = None
    source_waveform: list[float] | None = None
    master_waveform: list[float] | None = None
    source_spectrum: list[float] | None = None
    master_spectrum: list[float] | None = None
    source_level_timeline: list[float] | None = None
    master_level_timeline: list[float] | None = None
    target_lufs: float = -14.0
    maximum_gain_adjustment_db: float = 12.0
    ceiling_dbfs: float = -1.0
    eq_low_gain_db: float = 0.0
    eq_mid_gain_db: float = 0.0
    eq_high_gain_db: float = 0.0
    clipper_drive_db: float = 0.0
    limiter_lookahead_ms: float = 3.0
    limiter_release_ms: float = 80.0
    high_pass_enabled: bool = True
    high_pass_cutoff_hz: float = 25.0
    dynamic_eq_reduction_db: float = 0.0
    bass_control_reduction_db: float = 0.0
    de_esser_reduction_db: float = 0.0
    saturation_amount: float = 0.0
    ai_assist_enabled: bool = False
    bit_depth: int = 24
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime | None = None


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
        target_lufs: float = -14.0,
        maximum_gain_adjustment_db: float = 12.0,
        ceiling_dbfs: float = -1.0,
        eq_low_gain_db: float = 0.0,
        eq_mid_gain_db: float = 0.0,
        eq_high_gain_db: float = 0.0,
        clipper_drive_db: float = 0.0,
        limiter_lookahead_ms: float = 3.0,
        limiter_release_ms: float = 80.0,
        high_pass_enabled: bool = True,
        high_pass_cutoff_hz: float = 25.0,
        dynamic_eq_reduction_db: float = 0.0,
        bass_control_reduction_db: float = 0.0,
        de_esser_reduction_db: float = 0.0,
        saturation_amount: float = 0.0,
        ai_assist_enabled: bool = False,
        bit_depth: int = 24,
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
                        target_lufs=target_lufs,
                        maximum_gain_adjustment_db=maximum_gain_adjustment_db,
                        ceiling_dbfs=ceiling_dbfs,
                        eq_low_gain_db=eq_low_gain_db,
                        eq_mid_gain_db=eq_mid_gain_db,
                        eq_high_gain_db=eq_high_gain_db,
                        clipper_drive_db=clipper_drive_db,
                        limiter_lookahead_ms=limiter_lookahead_ms,
                        limiter_release_ms=limiter_release_ms,
                        high_pass_enabled=high_pass_enabled,
                        high_pass_cutoff_hz=high_pass_cutoff_hz,
                        dynamic_eq_reduction_db=dynamic_eq_reduction_db,
                        bass_control_reduction_db=bass_control_reduction_db,
                        de_esser_reduction_db=de_esser_reduction_db,
                        saturation_amount=saturation_amount,
                        ai_assist_enabled=ai_assist_enabled,
                        bit_depth=bit_depth,
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

    def mark_analysis_complete(self, job_id: str, result: dict[str, Any]) -> None:
        """Persist analysis and expose that mastering is now running."""
        self._update(job_id, status="mastering", result=result)

    def mark_mastered(
        self,
        job_id: str,
        *,
        recommendation: dict[str, Any],
        mastering_result: dict[str, Any],
        output_object_name: str,
        source_waveform: list[float],
        master_waveform: list[float],
        source_spectrum: list[float],
        master_spectrum: list[float],
        source_level_timeline: list[float],
        master_level_timeline: list[float],
    ) -> None:
        """Persist the auditable decision and downloadable master."""
        self._update(
            job_id,
            status="succeeded",
            recommendation=recommendation,
            mastering_result=mastering_result,
            output_object_name=output_object_name,
            source_waveform=source_waveform,
            master_waveform=master_waveform,
            source_spectrum=source_spectrum,
            master_spectrum=master_spectrum,
            source_level_timeline=source_level_timeline,
            master_level_timeline=master_level_timeline,
        )

    def mark_failed(self, job_id: str, code: str, message: str) -> None:
        """Persist a bounded public failure description."""
        self._update(
            job_id,
            status="failed",
            error_code=code[:64],
            error_message=message[:2000],
        )

    def save_interactive_settings(self, job_id: str, settings: dict[str, Any]) -> AnalysisJobRecord:
        """Persist validated preview settings without starting background work."""
        self._update(job_id, interactive_settings=settings)
        saved = self.get(job_id)
        if saved is None:
            raise KeyError(f"Unknown analysis job {job_id}")
        return saved

    def create_final_render(
        self,
        *,
        parent: AnalysisJobRecord,
        job_id: str,
        idempotency_key: str,
        settings: dict[str, Any],
    ) -> tuple[AnalysisJobRecord, bool]:
        """Create an idempotent child render reusing source and completed analysis."""
        existing = self.get_by_idempotency_key(idempotency_key)
        if existing is not None:
            return existing, False
        try:
            with self._engine.begin() as connection:
                connection.execute(
                    insert(analysis_jobs).values(
                        id=job_id,
                        idempotency_key=idempotency_key,
                        status="mastering",
                        object_name=parent.object_name,
                        original_filename=parent.original_filename,
                        attempt_count=0,
                        result=parent.result,
                        parent_job_id=parent.id,
                        initial_output_object_name=parent.initial_output_object_name
                        or parent.output_object_name,
                        interactive_settings=settings,
                        updated_at=datetime.now(UTC),
                        **settings,
                    )
                )
        except IntegrityError:
            raced = self.get_by_idempotency_key(idempotency_key)
            if raced is None:
                raise
            return raced, False
        created = self.get(job_id)
        if created is None:
            raise RuntimeError("Final render job disappeared after insertion")
        return created, True

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
        recommendation=row["recommendation"],
        mastering_result=row["mastering_result"],
        output_object_name=row["output_object_name"],
        initial_output_object_name=row["initial_output_object_name"],
        parent_job_id=row["parent_job_id"],
        interactive_settings=row["interactive_settings"],
        source_waveform=row["source_waveform"],
        master_waveform=row["master_waveform"],
        source_spectrum=row["source_spectrum"],
        master_spectrum=row["master_spectrum"],
        source_level_timeline=row["source_level_timeline"],
        master_level_timeline=row["master_level_timeline"],
        target_lufs=row["target_lufs"],
        maximum_gain_adjustment_db=row["maximum_gain_adjustment_db"],
        ceiling_dbfs=row["ceiling_dbfs"],
        eq_low_gain_db=row["eq_low_gain_db"],
        eq_mid_gain_db=row["eq_mid_gain_db"],
        eq_high_gain_db=row["eq_high_gain_db"],
        clipper_drive_db=row["clipper_drive_db"],
        limiter_lookahead_ms=row["limiter_lookahead_ms"],
        limiter_release_ms=row["limiter_release_ms"],
        high_pass_enabled=row["high_pass_enabled"],
        high_pass_cutoff_hz=row["high_pass_cutoff_hz"],
        dynamic_eq_reduction_db=row["dynamic_eq_reduction_db"],
        bass_control_reduction_db=row["bass_control_reduction_db"],
        de_esser_reduction_db=row["de_esser_reduction_db"],
        saturation_amount=row["saturation_amount"],
        ai_assist_enabled=row["ai_assist_enabled"],
        bit_depth=row["bit_depth"],
        error_code=row["error_code"],
        error_message=row["error_message"],
        created_at=row["created_at"],
    )
