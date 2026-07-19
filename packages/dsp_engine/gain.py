"""Deterministic gain staging processor."""

import math
from dataclasses import dataclass

import numpy as np

from packages.audio_core import FloatSamples


@dataclass(frozen=True, slots=True)
class GainProcessor:
    """Apply a fixed gain in dB without mutating the caller's sample buffer."""

    gain_db: float

    def __post_init__(self) -> None:
        """Reject non-finite configuration values."""
        if not math.isfinite(self.gain_db):
            raise ValueError("Gain must be finite")

    def process(self, samples: FloatSamples, sample_rate_hz: int) -> FloatSamples:
        """Return samples scaled by the configured linear gain factor."""
        _validate_audio(samples, sample_rate_hz)
        return np.asarray(samples * (10.0 ** (self.gain_db / 20.0)), dtype=np.float64)


def _validate_audio(samples: FloatSamples, sample_rate_hz: int) -> None:
    """Enforce the shape and finite-value contract shared by DSP processors."""
    if samples.ndim != 2 or samples.shape[0] < 1 or samples.shape[1] < 1:
        raise ValueError("Audio samples must have shape (frames, channels)")
    if sample_rate_hz < 1 or not np.isfinite(samples).all():
        raise ValueError("Audio samples and sample rate must be finite and positive")
