"""Tests for independently executable production task implementations."""

import wave
from pathlib import Path

import numpy as np

from packages.task_runtime.tasks import analyze_audio, export_wav


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
