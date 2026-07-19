"""FFmpeg-backed decoding for non-WAV audio formats."""

import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np

from .exceptions import InvalidAudioFileError, UnsupportedAudioFormatError
from .input_validation import validate_audio_path
from .limits import DEFAULT_DECODE_LIMITS, DecodeLimits
from .models import AudioMetadata, DecodedAudio

FFMPEG_SUFFIXES = frozenset({".aif", ".aiff", ".flac", ".m4a", ".mp3", ".ogg", ".opus"})


def decode_with_ffmpeg(
    path: str | Path, *, limits: DecodeLimits = DEFAULT_DECODE_LIMITS
) -> DecodedAudio:
    """Decode one supported stream into normalized samples and metadata."""
    audio_path = validate_audio_path(path)
    if audio_path.suffix.lower() not in FFMPEG_SUFFIXES:
        supported = ", ".join(sorted(FFMPEG_SUFFIXES))
        raise UnsupportedAudioFormatError(f"Unsupported audio format; supported: {supported}")
    stream = _probe_stream(audio_path, limits)
    sample_rate = _positive_integer(stream, "sample_rate")
    channels = _positive_integer(stream, "channels")
    duration = _positive_float(stream, "duration")
    if int(np.ceil(duration * sample_rate)) * channels > limits.max_sample_values:
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
                "-t",
                str(duration),
                "-f",
                "f64le",
                "-acodec",
                "pcm_f64le",
                "-",
            ],
            check=False,
            capture_output=True,
            timeout=limits.process_timeout_seconds,
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
    if values.size > limits.max_sample_values or not np.isfinite(values).all():
        raise InvalidAudioFileError("Decoded audio data is unsafe for analysis")
    frames = values.size // channels
    return DecodedAudio(
        values.reshape(frames, channels),
        AudioMetadata(
            sample_rate,
            channels,
            frames,
            _optional_positive_integer(stream, "bits_per_raw_sample"),
            audio_path.suffix[1:],
        ),
    )


def _probe_stream(path: Path, limits: DecodeLimits) -> dict[str, Any]:
    """Read first-stream metadata through FFprobe."""
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
            timeout=limits.process_timeout_seconds,
        )
    except FileNotFoundError as error:
        raise UnsupportedAudioFormatError("FFprobe is not installed") from error
    except subprocess.TimeoutExpired as error:
        raise InvalidAudioFileError("Audio probing exceeded the time limit") from error
    if completed.returncode != 0:
        raise InvalidAudioFileError("FFprobe could not inspect the audio file")
    try:
        stream = json.loads(completed.stdout)["streams"][0]
    except (IndexError, KeyError, TypeError, json.JSONDecodeError) as error:
        raise InvalidAudioFileError("Audio file has no readable audio stream") from error
    if not isinstance(stream, dict):
        raise InvalidAudioFileError("Audio stream metadata is invalid")
    return stream


def _positive_integer(stream: dict[str, Any], field: str) -> int:
    """Read one required positive integer FFprobe field."""
    value = _optional_positive_integer(stream, field)
    if value is None:
        raise InvalidAudioFileError(f"Audio stream has no valid {field}")
    return value


def _optional_positive_integer(stream: dict[str, Any], field: str) -> int | None:
    """Read one optional positive integer FFprobe field."""
    try:
        value = int(stream.get(field, 0))
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _positive_float(stream: dict[str, Any], field: str) -> float:
    """Read one required finite positive FFprobe field."""
    try:
        value = float(stream[field])
    except (KeyError, TypeError, ValueError) as error:
        raise InvalidAudioFileError(f"Audio stream has no valid {field}") from error
    if not np.isfinite(value) or value <= 0.0:
        raise InvalidAudioFileError(f"Audio stream has no valid {field}")
    return value
