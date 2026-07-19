"""Compatibility adapters for WAV decoding moved to :mod:`packages.audio_core`."""

from pathlib import Path

from packages.audio_core import MAX_SAMPLE_VALUES, FloatSamples, decode_wav

__all__ = ["FloatSamples", "MAX_SAMPLE_VALUES", "read_wav"]


def read_wav(path: str | Path) -> tuple[FloatSamples, int, int]:
    """Return the legacy tuple representation of decoded WAV audio."""
    decoded = decode_wav(path)
    metadata = decoded.metadata
    assert metadata.bit_depth is not None
    return decoded.samples, metadata.sample_rate_hz, metadata.bit_depth
