"""Typed contracts for decoded audio shared across OpenMaster packages."""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

FloatSamples = NDArray[np.float64]


@dataclass(frozen=True, slots=True)
class AudioMetadata:
    """Source metadata describing one decoded audio stream."""

    sample_rate_hz: int
    channels: int
    frame_count: int
    bit_depth: int | None
    source_format: str

    def __post_init__(self) -> None:
        """Validate metadata invariants required by every audio consumer."""
        if self.sample_rate_hz < 1 or self.channels < 1 or self.frame_count < 1:
            raise ValueError("Audio metadata dimensions must be positive")
        if self.bit_depth is not None and self.bit_depth < 1:
            raise ValueError("Audio bit depth must be positive when present")
        if not self.source_format:
            raise ValueError("Audio source format must not be empty")

    @property
    def duration_seconds(self) -> float:
        """Return decoded stream duration derived from frames and sample rate."""
        return self.frame_count / self.sample_rate_hz


@dataclass(frozen=True, slots=True)
class DecodedAudio:
    """Normalized samples paired with their validated source metadata."""

    samples: FloatSamples
    metadata: AudioMetadata

    def __post_init__(self) -> None:
        """Validate sample shape against metadata without copying the audio buffer."""
        if self.samples.ndim != 2:
            raise ValueError("Decoded samples must have shape (frames, channels)")
        if self.samples.shape != (self.metadata.frame_count, self.metadata.channels):
            raise ValueError("Decoded sample shape does not match audio metadata")
