"""Regression tests for the public analysis service."""

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
