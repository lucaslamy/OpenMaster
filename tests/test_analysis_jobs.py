"""Integration tests for durable upload and analysis-job coordination."""

from __future__ import annotations

from io import BytesIO
from typing import Any, cast

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from packages.analysis_jobs import AnalysisJobService, InvalidUploadError
from packages.database import AnalysisJobRepository, metadata
from packages.storage import MinioObjectStore


class FakeObjectStore:
    """Capture immutable uploads without a MinIO server."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def upload(
        self,
        object_name: str,
        stream: Any,
        *,
        length: int,
        content_type: str,
    ) -> None:
        del content_type
        self.objects[object_name] = stream.read(length)


def _repository() -> AnalysisJobRepository:
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    metadata.create_all(engine)
    return AnalysisJobRepository(engine)


def test_submit_persists_upload_and_dispatches_one_job() -> None:
    repository = _repository()
    storage = FakeObjectStore()
    dispatched: list[tuple[str, str]] = []
    service = AnalysisJobService(
        repository,
        cast(MinioObjectStore, storage),
        lambda job_id, object_name: dispatched.append((job_id, object_name)),
        maximum_upload_bytes=1024,
    )

    job = service.submit(
        filename="../../mix.mp3",
        content_type="audio/mpeg",
        stream=BytesIO(b"encoded-audio"),
        length=13,
        idempotency_key="request-1",
        target_lufs=-16.0,
        maximum_gain_adjustment_db=8.0,
        ceiling_dbfs=-1.5,
        eq_low_gain_db=1.0,
        eq_mid_gain_db=-0.5,
        eq_high_gain_db=1.5,
        clipper_drive_db=4.0,
        limiter_lookahead_ms=5.0,
        limiter_release_ms=120.0,
        high_pass_enabled=False,
        high_pass_cutoff_hz=32.0,
        dynamic_eq_reduction_db=3.0,
        bass_control_reduction_db=4.0,
        de_esser_reduction_db=5.0,
        saturation_amount=0.25,
        ai_assist_enabled=True,
        bit_depth=24,
    )

    assert job.status == "queued"
    assert job.original_filename == "mix.mp3"
    assert job.target_lufs == -16.0
    assert job.maximum_gain_adjustment_db == 8.0
    assert job.ceiling_dbfs == -1.5
    assert job.eq_low_gain_db == 1.0
    assert job.eq_mid_gain_db == -0.5
    assert job.eq_high_gain_db == 1.5
    assert job.clipper_drive_db == 4.0
    assert job.limiter_lookahead_ms == 5.0
    assert job.limiter_release_ms == 120.0
    assert job.high_pass_enabled is False
    assert job.high_pass_cutoff_hz == 32.0
    assert job.dynamic_eq_reduction_db == 3.0
    assert job.bass_control_reduction_db == 4.0
    assert job.de_esser_reduction_db == 5.0
    assert job.saturation_amount == 0.25
    assert job.ai_assist_enabled is True
    assert storage.objects[job.object_name] == b"encoded-audio"
    assert dispatched == [(job.id, job.object_name)]
    assert service.get(job.id) == job


def test_idempotent_retry_returns_same_job_without_second_upload() -> None:
    repository = _repository()
    storage = FakeObjectStore()
    dispatched: list[tuple[str, str]] = []
    service = AnalysisJobService(
        repository,
        cast(MinioObjectStore, storage),
        lambda job_id, object_name: dispatched.append((job_id, object_name)),
        maximum_upload_bytes=1024,
    )
    arguments = {
        "filename": "mix.mp3",
        "content_type": "audio/mpeg",
        "length": 5,
        "idempotency_key": "same-request",
    }

    first = service.submit(stream=BytesIO(b"first"), **arguments)
    second = service.submit(stream=BytesIO(b"other"), **arguments)

    assert second.id == first.id
    assert len(storage.objects) == 1
    assert dispatched == [(first.id, first.object_name), (first.id, first.object_name)]


@pytest.mark.parametrize(
    ("filename", "length", "message"),
    [
        ("notes.txt", 5, "Unsupported audio format"),
        ("empty.wav", 0, "empty"),
        ("huge.wav", 2048, "MAX_UPLOAD_BYTES"),
    ],
)
def test_submit_rejects_invalid_uploads(filename: str, length: int, message: str) -> None:
    service = AnalysisJobService(
        _repository(),
        cast(MinioObjectStore, FakeObjectStore()),
        lambda _job_id, _object_name: None,
        maximum_upload_bytes=1024,
    )

    with pytest.raises(InvalidUploadError, match=message):
        service.submit(
            filename=filename,
            content_type="application/octet-stream",
            stream=BytesIO(b"x"),
            length=length,
            idempotency_key="request",
        )


@pytest.mark.parametrize(
    ("setting", "value", "message"),
    [
        ("target_lufs", -30.0, "target_lufs"),
        ("maximum_gain_adjustment_db", 13.0, "maximum_gain_adjustment_db"),
        ("ceiling_dbfs", 0.0, "ceiling_dbfs"),
        ("eq_low_gain_db", 7.0, "equalizer"),
        ("clipper_drive_db", 13.0, "clipper_drive_db"),
        ("limiter_lookahead_ms", 11.0, "limiter_lookahead_ms"),
        ("limiter_release_ms", 501.0, "limiter_release_ms"),
        ("high_pass_cutoff_hz", 81.0, "high_pass_cutoff_hz"),
        ("dynamic_eq_reduction_db", 13.0, "selective dynamics"),
        ("bass_control_reduction_db", 13.0, "selective dynamics"),
        ("de_esser_reduction_db", 13.0, "selective dynamics"),
        ("saturation_amount", 1.1, "saturation_amount"),
        ("bit_depth", 20, "bit_depth"),
    ],
)
def test_submit_rejects_unsafe_mastering_policy(
    setting: str,
    value: float,
    message: str,
) -> None:
    service = AnalysisJobService(
        _repository(),
        cast(MinioObjectStore, FakeObjectStore()),
        lambda _job_id, _object_name: None,
        maximum_upload_bytes=1024,
    )
    arguments: dict[str, object] = {
        "filename": "mix.wav",
        "content_type": "audio/wav",
        "stream": BytesIO(b"audio"),
        "length": 5,
        "idempotency_key": f"unsafe-{setting}",
        setting: value,
    }
    with pytest.raises(InvalidUploadError, match=message):
        service.submit(**arguments)  # type: ignore[arg-type]


def test_repository_persists_worker_result_and_failure() -> None:
    repository = _repository()
    job, _ = repository.create_or_get(
        job_id="job-1",
        idempotency_key="request-1",
        object_name="analysis/job-1/source.wav",
        original_filename="source.wav",
    )

    repository.mark_running(job.id)
    repository.mark_analysis_complete(job.id, {"lufs": -14.0})
    analysing = repository.get(job.id)
    assert analysing is not None
    assert analysing.status == "mastering"
    repository.mark_mastered(
        job.id,
        recommendation={"confidence": 0.9},
        mastering_result={"processors": ["gain"]},
        output_object_name="mastering/job-1/master.wav",
        source_waveform=[0.25] * 16,
        master_waveform=[0.5] * 16,
        source_spectrum=[0.2] * 16,
        master_spectrum=[0.3] * 16,
        source_level_timeline=[0.4] * 16,
        master_level_timeline=[0.6] * 16,
    )
    completed = repository.get(job.id)
    assert completed is not None
    assert completed.status == "succeeded"
    assert completed.attempt_count == 1
    assert completed.result == {"lufs": -14.0}
    assert completed.recommendation == {"confidence": 0.9}
    assert completed.output_object_name == "mastering/job-1/master.wav"
    assert completed.source_waveform == [0.25] * 16
    assert completed.master_waveform == [0.5] * 16
    assert completed.source_spectrum == [0.2] * 16
    assert completed.master_spectrum == [0.3] * 16
    assert completed.source_level_timeline == [0.4] * 16
    assert completed.master_level_timeline == [0.6] * 16

    repository.mark_failed(job.id, "DecodeError", "invalid audio")
    failed = repository.get(job.id)
    assert failed is not None
    assert failed.status == "failed"
    assert failed.error_code == "DecodeError"


def test_final_render_reuses_source_and_analysis() -> None:
    repository = _repository()
    parent, _ = repository.create_or_get(
        job_id="parent",
        idempotency_key="initial",
        object_name="analysis/parent/source.wav",
        original_filename="source.wav",
    )
    repository.mark_analysis_complete(parent.id, {"integrated_lufs": -14.0})
    repository.mark_mastered(
        parent.id,
        recommendation={},
        mastering_result={},
        output_object_name="mastering/parent/initial.wav",
        source_waveform=[],
        master_waveform=[],
        source_spectrum=[],
        master_spectrum=[],
        source_level_timeline=[],
        master_level_timeline=[],
    )
    completed = repository.get(parent.id)
    assert completed is not None
    child, created = repository.create_final_render(
        parent=completed,
        job_id="child",
        idempotency_key="final:parent:key",
        settings={"eq_low_gain_db": 2.0},
    )
    assert created
    assert child.status == "mastering"
    assert child.object_name == parent.object_name
    assert child.result == {"integrated_lufs": -14.0}
    assert child.parent_job_id == parent.id
    assert child.initial_output_object_name == "mastering/parent/initial.wav"
