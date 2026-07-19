"""Deterministic linked sample-peak limiter."""

import math
from dataclasses import dataclass

import numpy as np

from packages.audio_core import FloatSamples

from .gain import _validate_audio


@dataclass(frozen=True, slots=True)
class LimiterProcessor:
    """Constrain each frame to a linked sample-peak ceiling in dBFS."""

    ceiling_dbfs: float = -1.0

    def __post_init__(self) -> None:
        """Reject non-finite or above-full-scale output ceilings."""
        if not math.isfinite(self.ceiling_dbfs) or self.ceiling_dbfs > 0.0:
            raise ValueError("Limiter ceiling must be finite and at or below 0 dBFS")

    def process(self, samples: FloatSamples, sample_rate_hz: int) -> FloatSamples:
        """Apply linked instantaneous gain reduction without modifying input samples."""
        _validate_audio(samples, sample_rate_hz)
        ceiling = 10.0 ** (self.ceiling_dbfs / 20.0)
        frame_peaks = np.max(np.abs(samples), axis=1, keepdims=True)
        gains = np.minimum(1.0, ceiling / np.maximum(frame_peaks, np.finfo(np.float64).tiny))
        return np.asarray(samples * gains, dtype=np.float64)
