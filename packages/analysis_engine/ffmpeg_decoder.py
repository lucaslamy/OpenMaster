"""FFmpeg-backed decoding for supported non-WAV audio formats."""

import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

from .exceptions import InvalidAudioFileError, UnsupportedAudioFormatError
from .wav_reader import MAX_SAMPLE_VALUES, FloatSamples, validate_audio_path

SUPPORTED_FORMATS = frozenset({".aif", ".aiff", ".flac", ".m4a", ".mp3", ".ogg", ".opus"})
_PROCESS_TIMEOUT_SECONDS = 120


def read_with_ffmpeg(path: str | Path) -> tuple[FloatSamples, int, int | None]:
    """Decode one supported audio stream into normalized float64 samples.

    FFprobe establishes stream dimensions before FFmpeg is started. This enforces the
    same allocation limit as the native WAV decoder and avoids trusting file suffixes.
    """
    audio_path = validate_audio_path(path)
    if audio_path.suffix.lower() not in SUPPORTED_FORMATS:
        supported = ", ".join(sorted(SUPPORTED_FORMATS))
        raise UnsupportedAudioFormatError(f"Unsupported audio format; supported: {supported}")

    stream = _probe_stream(audio_path)
    sample_rate = _positive_integer(stream, "sample_rate")
    channels = _positive_integer(stream, "channels")
    duration = _positive_float(stream, "duration")
    estimated_values = int(np.ceil(duration * sample_rate)) * channels
    if estimated_values > MAX_SAMPLE_VALUES:
        raise InvalidAudioFileError("Audio file exceeds the analysis sample limit")

    try:
        completed = subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-nostdin",
                "-i",
                str(audio_path),
                "-map",
                "0:a:0",
                "-f",
                "f64le",
                "-acodec",
                "pcm_f64le",
                "-",
            ],
            check=False,
            capture_output=True,
            timeout=_PROCESS_TIMEOUT_SECONDS,
        )
    except FileNotFoundError as error:
        raise UnsupportedAudioFormatError("FFmpeg is not installed") from error
    except subprocess.TimeoutExpired as error:
        raise InvalidAudioFileError("Audio decoding exceeded the time limit") from error
    if completed.returncode != 0:
        raise InvalidAudioFileError("FFmpeg could not decode the audio file")

    values = np.frombuffer(completed.stdout, dtype="<f8")
    if values.size == 0 or values.size % channels != 0:
        raise InvalidAudioFileError("Decoded audio data has invalid dimensions")
    if values.size > MAX_SAMPLE_VALUES or not np.isfinite(values).all():
        raise InvalidAudioFileError("Decoded audio data is unsafe for analysis")
    bit_depth = _optional_positive_integer(stream, "bits_per_raw_sample")
    return values.reshape(-1, channels), sample_rate, bit_depth


def _probe_stream(path: Path) -> dict[str, Any]:
    """Return metadata for the first audio stream, or a typed input error."""
    try:
        completed = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a:0",
                "-show_entries",
                "stream=sample_rate,channels,duration,bits_per_raw_sample",
                "-of",
                "json",
                str(path),
            ],
            check=False,
            capture_output=True,
            timeout=_PROCESS_TIMEOUT_SECONDS,
        )
    except FileNotFoundError as error:
        raise UnsupportedAudioFormatError("FFprobe is not installed") from error
    except subprocess.TimeoutExpired as error:
        raise InvalidAudioFileError("Audio probing exceeded the time limit") from error
    if completed.returncode != 0:
        raise InvalidAudioFileError("FFprobe could not inspect the audio file")
    try:
        payload = json.loads(completed.stdout)
        streams = payload["streams"]
        stream = streams[0]
    except (IndexError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise InvalidAudioFileError("Audio file has no readable audio stream") from error
    if not isinstance(stream, dict):
        raise InvalidAudioFileError("Audio stream metadata is invalid")
    return stream


def _positive_integer(stream: dict[str, Any], field: str) -> int:
    """Read a required positive integer field from FFprobe metadata."""
    value = _optional_positive_integer(stream, field)
    if value is None:
        raise InvalidAudioFileError(f"Audio stream has no valid {field}")
    return value


def _optional_positive_integer(stream: dict[str, Any], field: str) -> int | None:
    """Read an optional positive integer field from FFprobe metadata."""
    try:
        value = int(stream.get(field, 0))
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _positive_float(stream: dict[str, Any], field: str) -> float:
    """Read a required finite positive float field from FFprobe metadata."""
    try:
        value = float(stream[field])
    except (KeyError, TypeError, ValueError) as error:
        raise InvalidAudioFileError(f"Audio stream has no valid {field}") from error
    if not np.isfinite(value) or value <= 0.0:
        raise InvalidAudioFileError(f"Audio stream has no valid {field}")
    return value
