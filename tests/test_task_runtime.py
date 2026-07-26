"""Tests for independently executable production task implementations."""

import wave
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from packages.database import AnalysisJobRecord
from packages.dsp_engine import MasteringPolicy
from packages.task_runtime.tasks import (
    _master_filename,
    _policy_changes,
    analyze_audio,
    export_wav,
)


def test_analysis_and_export_task_run_without_a_broker(tmp_path: Path) -> None:
    source = tmp_path / "source.wav"
    output = tmp_path / "output.wav"
    with wave.open(str(source), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(48_000)
        stream.writeframes(np.zeros(48_000, dtype="<i2").tobytes())

    assert analyze_audio.run(str(source))["channels"] == 1
    assert export_wav.run(str(source), str(output))["output_path"] == str(output)
    assert output.is_file()


def test_master_filename_preserves_source_identity_and_is_retry_stable() -> None:
    job = AnalysisJobRecord(
        id="job-1",
        status="mastering",
        object_name="analysis/job-1/source.wav",
        original_filename="My final mix!.wav",
        attempt_count=1,
        bit_depth=24,
        created_at=datetime(2026, 7, 25, 12, 34, 56, tzinfo=UTC),
    )

    assert _master_filename(job) == "My-final-mix-24bit-openmaster-20260725T123456Z.wav"


def test_policy_changes_reports_only_exact_lamai_overrides() -> None:
    before = MasteringPolicy(target_lufs=-14, eq_low_gain_db=0)
    after = MasteringPolicy(target_lufs=-11, eq_low_gain_db=1.5)

    assert _policy_changes(before, after) == [
        {"parameter": "target_lufs", "before": -14, "after": -11},
        {"parameter": "eq_low_gain_db", "before": 0, "after": 1.5},
    ]
