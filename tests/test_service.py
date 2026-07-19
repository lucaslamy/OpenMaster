"""Regression tests for the public analysis service."""

import json
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
import pytest

from packages.analysis_engine import AnalysisService
from packages.analysis_engine.exceptions import InvalidAudioFileError, UnsupportedAudioFormatError


def _write_wav(path: Path, samples: np.ndarray, sample_rate: int = 48_000) -> None:
    pcm = np.clip(samples, -1.0, 1.0 - 1 / 32768) * 32768
    with wave.open(str(path), "wb") as target:
        target.setnchannels(samples.shape[1])
        target.setsampwidth(2)
        target.setframerate(sample_rate)
        target.writeframes(pcm.astype("<i2").tobytes())


def _write_24_bit_wav(path: Path, samples: np.ndarray, sample_rate: int = 48_000) -> None:
    """Write normalized samples as little-endian signed 24-bit PCM WAV."""
    pcm = np.clip(samples, -1.0, 1.0 - 1 / 8388608) * 8388608
    values = pcm.astype(np.int32).reshape(-1)
    encoded = np.empty((values.size, 3), dtype=np.uint8)
    encoded[:, 0] = values & 0xFF
    encoded[:, 1] = (values >> 8) & 0xFF
    encoded[:, 2] = (values >> 16) & 0xFF
    with wave.open(str(path), "wb") as target:
        target.setnchannels(samples.shape[1])
        target.setsampwidth(3)
        target.setframerate(sample_rate)
        target.writeframes(encoded.tobytes())


def test_analyze_stereo_sine_returns_signal_measurements(tmp_path: Path) -> None:
    sample_rate = 48_000
    time = np.arange(sample_rate * 2) / sample_rate
    sine = 0.5 * np.sin(2 * np.pi * 440 * time)
    audio_path = tmp_path / "tone.wav"
    _write_wav(audio_path, np.column_stack((sine, sine)))

    result = AnalysisService().analyze(audio_path)

    assert result.duration_seconds == pytest.approx(2.0)
    assert result.sample_rate_hz == sample_rate
    assert result.bit_depth == 16
    assert result.channels == 2
    assert result.rms_dbfs == pytest.approx(-9.03, abs=0.1)
    assert result.peak_dbfs == pytest.approx(-6.02, abs=0.1)
    assert result.true_peak_dbfs >= result.peak_dbfs
    assert result.crest_factor_db == pytest.approx(3.01, abs=0.15)
    assert result.phase_correlation == pytest.approx(1.0)
    assert result.stereo_width == pytest.approx(0.0, abs=1e-6)
    assert result.spectral_centroid_hz == pytest.approx(440, abs=20)
    assert result.musical_key is not None
    assert result.to_dict()["sample_rate_hz"] == sample_rate


def test_analyze_rejects_missing_and_unsupported_files(tmp_path: Path) -> None:
    service = AnalysisService()
    with pytest.raises(InvalidAudioFileError):
        service.analyze(tmp_path / "missing.wav")
    unsupported = tmp_path / "audio.mp3"
    unsupported.write_bytes(b"not audio")
    with pytest.raises(UnsupportedAudioFormatError):
        service.analyze(unsupported)


def test_analyze_mono_silence_has_safe_unavailable_measurements(tmp_path: Path) -> None:
    audio_path = tmp_path / "silence.wav"
    _write_wav(audio_path, np.zeros((48_000, 1)))

    result = AnalysisService().analyze(audio_path)

    assert result.channels == 1
    assert result.lufs is None
    assert result.bpm is None
    assert result.musical_key is None
    assert result.stereo_width is None
    assert result.phase_correlation is None
    assert result.dynamic_range_db == 0.0


def test_analyze_24_bit_pcm_preserves_metadata_and_level(tmp_path: Path) -> None:
    sample_rate = 48_000
    time = np.arange(sample_rate) / sample_rate
    audio_path = tmp_path / "tone-24.wav"
    _write_24_bit_wav(audio_path, (0.25 * np.sin(2 * np.pi * 1_000 * time))[:, np.newaxis])

    result = AnalysisService().analyze(audio_path)

    assert result.bit_depth == 24
    assert result.channels == 1
    assert result.rms_dbfs == pytest.approx(-15.05, abs=0.1)


def test_command_line_interface_serializes_result_and_input_errors(tmp_path: Path) -> None:
    audio_path = tmp_path / "silence.wav"
    _write_wav(audio_path, np.zeros((48_000, 1)))

    success = subprocess.run(
        [sys.executable, "-m", "packages.analysis_engine", str(audio_path)],
        check=False,
        capture_output=True,
        text=True,
    )
    failure = subprocess.run(
        [sys.executable, "-m", "packages.analysis_engine", str(tmp_path / "missing.wav")],
        check=False,
        capture_output=True,
        text=True,
    )

    assert success.returncode == 0
    assert json.loads(success.stdout)["channels"] == 1
    assert failure.returncode == 2
    assert "does not exist" in json.loads(failure.stderr)["error"]


def test_analyze_estimates_tempo_and_key_for_controlled_signals(tmp_path: Path) -> None:
    sample_rate = 48_000
    click_track = np.zeros(sample_rate * 10)
    for start in range(0, click_track.size, sample_rate // 2):
        click_track[start : start + 500] = np.hanning(500)
    tempo_path = tmp_path / "clicks.wav"
    _write_wav(tempo_path, click_track[:, np.newaxis])

    time = np.arange(sample_rate * 4) / sample_rate
    c_major = (
        sum(np.sin(2 * np.pi * frequency * time) for frequency in (261.6256, 329.6276, 391.9954))
        / 3
    )
    key_path = tmp_path / "c-major.wav"
    _write_wav(key_path, c_major[:, np.newaxis])

    tempo_result = AnalysisService().analyze(tempo_path)
    key_result = AnalysisService().analyze(key_path)

    assert tempo_result.bpm == pytest.approx(120.0, abs=1.0)
    assert key_result.musical_key == "C major"
