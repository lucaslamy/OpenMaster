"""Deterministic three-band parametric equalizer."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.signal import sosfilt

from packages.audio_core import FloatSamples

from .gain import _validate_audio


@dataclass(frozen=True, slots=True)
class TonalEqualizerProcessor:
    """Apply fixed low, mid, and high peaking filters without hidden analysis."""

    low_gain_db: float = 0.0
    mid_gain_db: float = 0.0
    high_gain_db: float = 0.0

    def __post_init__(self) -> None:
        """Keep tonal corrections finite and deliberately conservative."""
        gains = (self.low_gain_db, self.mid_gain_db, self.high_gain_db)
        if not all(math.isfinite(gain) and -6.0 <= gain <= 6.0 for gain in gains):
            raise ValueError("Equalizer gains must be finite and between -6 and 6 dB")

    def process(self, samples: FloatSamples, sample_rate_hz: int) -> FloatSamples:
        """Process three musical frequency regions using stable RBJ biquads."""
        _validate_audio(samples, sample_rate_hz)
        output = np.asarray(samples, dtype=np.float64).copy()
        bands = (
            (100.0, 0.7, self.low_gain_db),
            (1_000.0, 1.0, self.mid_gain_db),
            (10_000.0, 0.7, self.high_gain_db),
        )
        for frequency_hz, quality_factor, gain_db in bands:
            if gain_db == 0.0 or frequency_hz >= sample_rate_hz * 0.49:
                continue
            output = np.asarray(
                sosfilt(
                    _peaking_sos(frequency_hz, quality_factor, gain_db, sample_rate_hz),
                    output,
                    axis=0,
                ),
                dtype=np.float64,
            )
        return output


def _peaking_sos(
    frequency_hz: float,
    quality_factor: float,
    gain_db: float,
    sample_rate_hz: int,
) -> np.ndarray:
    """Return one normalized RBJ peaking-EQ second-order section."""
    amplitude = 10.0 ** (gain_db / 40.0)
    omega = 2.0 * math.pi * frequency_hz / sample_rate_hz
    alpha = math.sin(omega) / (2.0 * quality_factor)
    cosine = math.cos(omega)
    b0 = 1.0 + alpha * amplitude
    b1 = -2.0 * cosine
    b2 = 1.0 - alpha * amplitude
    a0 = 1.0 + alpha / amplitude
    a1 = -2.0 * cosine
    a2 = 1.0 - alpha / amplitude
    return np.array([[b0 / a0, b1 / a0, b2 / a0, 1.0, a1 / a0, a2 / a0]])
