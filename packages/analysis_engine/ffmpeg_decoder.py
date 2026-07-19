"""Compatibility adapters for FFmpeg decoding moved to :mod:`packages.audio_core`."""

from pathlib import Path

from packages.audio_core import FFMPEG_SUFFIXES, FloatSamples, decode_with_ffmpeg

SUPPORTED_FORMATS = FFMPEG_SUFFIXES


def read_with_ffmpeg(path: str | Path) -> tuple[FloatSamples, int, int | None]:
    """Return the legacy tuple representation of decoded FFmpeg audio."""
    decoded = decode_with_ffmpeg(path)
    metadata = decoded.metadata
    return decoded.samples, metadata.sample_rate_hz, metadata.bit_depth
