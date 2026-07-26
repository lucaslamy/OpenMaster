"""Oversampled linked soft clipper for controlled transient density."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.signal import resample_poly

from packages.audio_core import FloatSamples

from .gain import _validate_audio


@dataclass(frozen=True, slots=True)
class OversampledClipperProcessor:
    """Drive a smooth saturating curve at a higher internal sample rate."""

    drive_db: float = 0.0
    oversample_factor: int = 4

    def __post_init__(self) -> None:
        """Reject unsafe drive and unsupported oversampling ratios."""
        if not math.isfinite(self.drive_db) or not 0.0 <= self.drive_db <= 12.0:
            raise ValueError("Clipper drive must be finite and between 0 and 12 dB")
        if self.oversample_factor not in (2, 4, 8):
            raise ValueError("Clipper oversample factor must be 2, 4, or 8")

    def process(self, samples: FloatSamples, sample_rate_hz: int) -> FloatSamples:
        """Apply normalized tanh clipping and return the original frame count."""
        _validate_audio(samples, sample_rate_hz)
        if self.drive_db == 0.0:
            return np.asarray(samples, dtype=np.float64).copy()
        factor = self.oversample_factor
        oversampled = resample_poly(samples, factor, 1, axis=0)
        drive = 10.0 ** (self.drive_db / 20.0)
        # Normalize the curve at full scale instead of dividing by the drive.
        # Dividing by ``drive`` flattened peaks but also attenuated the entire
        # programme, making increasing drive sound quieter—the opposite of the
        # intended mastering behaviour.
        clipped = np.tanh(oversampled * drive) / math.tanh(drive)
        output = resample_poly(clipped, 1, factor, axis=0)
        # The reconstruction filter can overshoot the normalized curve around
        # discontinuities. Keep the clipper's public full-scale contract bounded;
        # the following true-peak limiter remains the authoritative ceiling.
        return np.asarray(np.clip(output[: samples.shape[0]], -1.0, 1.0), dtype=np.float64)
