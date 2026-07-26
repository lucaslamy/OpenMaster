"""Oversampled gentle saturation for controlled harmonic density."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.signal import resample_poly

from packages.audio_core import FloatSamples

from .gain import _validate_audio


@dataclass(frozen=True, slots=True)
class SaturationProcessor:
    """Blend a level-compensated soft curve with the dry signal."""

    amount: float = 0.0
    oversample_factor: int = 4

    def __post_init__(self) -> None:
        """Limit saturation to a subtle mastering-oriented range."""
        if not math.isfinite(self.amount) or not 0.0 <= self.amount <= 1.0:
            raise ValueError("Saturation amount must be between 0 and 1")
        if self.oversample_factor not in (2, 4, 8):
            raise ValueError("Saturation oversample factor must be 2, 4, or 8")

    def process(self, samples: FloatSamples, sample_rate_hz: int) -> FloatSamples:
        """Apply an oversampled tanh curve while preserving the original length."""
        _validate_audio(samples, sample_rate_hz)
        if self.amount == 0.0:
            return np.asarray(samples, dtype=np.float64).copy()
        factor = self.oversample_factor
        oversampled = resample_poly(samples, factor, 1, axis=0)
        drive = 1.0 + 2.0 * self.amount
        saturated = np.tanh(oversampled * drive) / math.tanh(drive)
        mixed = oversampled * (1.0 - self.amount * 0.35) + saturated * (self.amount * 0.35)
        output = resample_poly(mixed, 1, factor, axis=0)
        return np.asarray(output[: samples.shape[0]], dtype=np.float64)
