"""Regression tests for the public analysis service."""

import json
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
import pytest
from scipy.io import wavfile

from packages.analysis_engine import AnalysisService
from packages.analysis_engine.exceptions import InvalidAudioFileError, UnsupportedAudioFormatError
from packages.analysis_engine.metrics import estimate_bpm
from packages.audio_core import decode_audio


def _ffmpeg_ebur128_summary(path: Path) -> tuple[float, float]:
    """Return FFmpeg ebur128 integrated loudness and true peak from its summary."""
    completed = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-filter_complex",
            "ebur128=peak=true",
            "-f",
            "null",
            "-",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    summary = completed.stderr.split("Summary:", maxsplit=1)[-1]
    loudness = re.search(r"Integrated loudness:.*?I:\s*(-?\d+(?:\.\d+)?) LUFS", summary, re.DOTALL)
    true_peak = re.search(r"True peak:.*?Peak:\s*(-?\d+(?:\.\d+)?) dBFS", summary, re.DOTALL)
    assert loudness is not None
    assert true_peak is not None
    return float(loudness.group(1)), float(true_peak.group(1))


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


def test_analyze_decoded_matches_path_analysis_without_a_second_decode(tmp_path: Path) -> None:
    audio_path = tmp_path / "tone.wav"
    _write_wav(audio_path, np.full((48_000, 1), 0.25))
    decoded = decode_audio(audio_path)

    assert AnalysisService().analyze_decoded(decoded) == AnalysisService().analyze(audio_path)


def test_integrated_loudness_sums_dual_mono_channel_energy(tmp_path: Path) -> None:
    sample_rate = 48_000
    time = np.arange(sample_rate * 5) / sample_rate
    sine = 0.5 * np.sin(2 * np.pi * 1_000 * time)
    mono_path = tmp_path / "mono.wav"
    stereo_path = tmp_path / "dual-mono.wav"
    _write_wav(mono_path, sine[:, np.newaxis])
    _write_wav(stereo_path, np.column_stack((sine, sine)))

    mono_lufs = AnalysisService().analyze(mono_path).lufs
    stereo_lufs = AnalysisService().analyze(stereo_path).lufs

    assert mono_lufs is not None
    assert stereo_lufs == pytest.approx(mono_lufs + 3.0103, abs=0.02)


@pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="FFmpeg is required for reference checks"
)
@pytest.mark.parametrize("channels", [1, 2])
def test_loudness_and_true_peak_cross_validate_with_ffmpeg(tmp_path: Path, channels: int) -> None:
    sample_rate = 48_000
    time = np.arange(sample_rate * 5) / sample_rate
    sine = 0.5 * np.sin(2 * np.pi * 1_000 * time)
    samples = sine[:, np.newaxis] if channels == 1 else np.column_stack((sine, sine))
    audio_path = tmp_path / f"reference-{channels}.wav"
    _write_wav(audio_path, samples)

    result = AnalysisService().analyze(audio_path)
    reference_lufs, reference_true_peak = _ffmpeg_ebur128_summary(audio_path)

    assert result.lufs == pytest.approx(reference_lufs, abs=0.35)
    assert result.true_peak_dbfs == pytest.approx(reference_true_peak, abs=0.35)


def test_analyze_rejects_missing_and_unsupported_files(tmp_path: Path) -> None:
    service = AnalysisService()
    with pytest.raises(InvalidAudioFileError):
        service.analyze(tmp_path / "missing.wav")
    unsupported = tmp_path / "audio.txt"
    unsupported.write_bytes(b"not audio")
    with pytest.raises(UnsupportedAudioFormatError):
        service.analyze(unsupported)
    corrupt = tmp_path / "corrupt.mp3"
    corrupt.write_bytes(b"not audio")
    with pytest.raises(InvalidAudioFileError):
        service.analyze(corrupt)


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


def test_analyze_32_bit_float_wav(tmp_path: Path) -> None:
    sample_rate = 48_000
    time = np.arange(sample_rate) / sample_rate
    audio_path = tmp_path / "tone-float.wav"
    samples = (0.5 * np.sin(2 * np.pi * 440 * time)).astype(np.float32)
    wavfile.write(audio_path, sample_rate, samples)

    result = AnalysisService().analyze(audio_path)

    assert result.bit_depth == 32
    assert result.channels == 1
    assert result.rms_dbfs == pytest.approx(-9.03, abs=0.1)


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


def test_mastering_command_line_interface_exports_auditable_wav(tmp_path: Path) -> None:
    audio_path = tmp_path / "mix.wav"
    output_path = tmp_path / "master.wav"
    _write_wav(audio_path, np.full((48_000, 1), 0.25))

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "packages.dsp_engine",
            str(audio_path),
            str(output_path),
            "--target-lufs",
            "-16",
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    payload = json.loads(completed.stdout)

    assert completed.returncode == 0
    assert payload["output_path"] == str(output_path)
    assert payload["processors"] == ["gain", "sample_peak_limiter"]
    assert output_path.is_file()


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


@pytest.mark.parametrize("expected_bpm", [60, 90, 100, 120, 150, 180, 200])
def test_tempo_estimator_avoids_half_tempo_for_click_tracks(expected_bpm: int) -> None:
    sample_rate = 48_000
    click_track = np.zeros(sample_rate * 8)
    period = round(sample_rate * 60 / expected_bpm)
    for start in range(0, click_track.size, period):
        click_track[start : start + 500] = np.hanning(500)

    estimated_bpm = estimate_bpm(click_track, sample_rate)

    assert estimated_bpm == pytest.approx(expected_bpm, abs=2.0)


@pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="FFmpeg and FFprobe are required for compressed-format integration tests",
)
@pytest.mark.parametrize("suffix", [".aiff", ".flac", ".m4a", ".mp3", ".ogg", ".opus"])
def test_analyze_ffmpeg_supported_format(tmp_path: Path, suffix: str) -> None:
    source_path = tmp_path / "source.wav"
    _write_wav(source_path, np.full((48_000, 1), 0.25))
    encoded_path = tmp_path / f"source{suffix}"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(source_path), str(encoded_path)],
        check=True,
        capture_output=True,
    )

    result = AnalysisService().analyze(encoded_path)

    assert result.sample_rate_hz == 48_000
    assert result.channels == 1
    assert result.duration_seconds == pytest.approx(1.0, abs=0.1)
    assert np.isfinite(result.rms_dbfs)
    assert np.isfinite(result.peak_dbfs)
    assert np.isfinite(result.true_peak_dbfs)
