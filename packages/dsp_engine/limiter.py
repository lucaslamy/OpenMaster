"""Oversampled linked lookahead limiter with deterministic release smoothing."""

import math
from collections import deque
from dataclasses import dataclass

import numpy as np
from scipy.signal import resample_poly

from packages.audio_core import FloatSamples

from .gain import _validate_audio


@dataclass(frozen=True, slots=True)
class LimiterProcessor:
    """Constrain linked channels using oversampled peak detection."""

    ceiling_dbfs: float = -1.0
    lookahead_ms: float = 3.0
    release_ms: float = 80.0
    oversample_factor: int = 4

    def __post_init__(self) -> None:
        """Reject non-finite or above-full-scale output ceilings."""
        if not math.isfinite(self.ceiling_dbfs) or self.ceiling_dbfs > 0.0:
            raise ValueError("Limiter ceiling must be finite and at or below 0 dBFS")
        if not math.isfinite(self.lookahead_ms) or not 0.0 <= self.lookahead_ms <= 10.0:
            raise ValueError("Limiter lookahead must be between 0 and 10 ms")
        if not math.isfinite(self.release_ms) or not 10.0 <= self.release_ms <= 500.0:
            raise ValueError("Limiter release must be between 10 and 500 ms")
        if self.oversample_factor not in (2, 4, 8):
            raise ValueError("Limiter oversample factor must be 2, 4, or 8")

    def process(self, samples: FloatSamples, sample_rate_hz: int) -> FloatSamples:
        """Apply linked lookahead gain reduction without modifying input samples."""
        _validate_audio(samples, sample_rate_hz)
        factor = self.oversample_factor
        working_rate = sample_rate_hz * factor
        oversampled = resample_poly(samples, factor, 1, axis=0)
        ceiling = 10.0 ** (self.ceiling_dbfs / 20.0)
        frame_peaks = np.max(np.abs(oversampled), axis=1)
        lookahead_frames = round(self.lookahead_ms * working_rate / 1000.0)
        future_peaks = _future_maximum(frame_peaks, lookahead_frames)
        desired = np.minimum(
            1.0,
            ceiling / np.maximum(future_peaks, np.finfo(np.float64).tiny),
        )
        release_coefficient = math.exp(-1.0 / (self.release_ms * working_rate / 1000.0))
        gains = np.empty_like(desired)
        current = 1.0
        for index, target in enumerate(desired):
            current = min(float(target), 1.0 - (1.0 - current) * release_coefficient)
            gains[index] = current
        limited = oversampled * gains[:, np.newaxis]
        output = resample_poly(limited, 1, factor, axis=0)[: samples.shape[0]]
        reconstructed_peak = float(np.max(np.abs(resample_poly(output, factor, 1, axis=0))))
        if reconstructed_peak > ceiling:
            output = output * (ceiling / reconstructed_peak)
        # Resampling can create a minute reconstruction overshoot; this final linked
        # guard enforces the public ceiling without changing normal frames.
        frame_output_peaks = np.max(np.abs(output), axis=1, keepdims=True)
        guard = np.minimum(
            1.0,
            ceiling / np.maximum(frame_output_peaks, np.finfo(np.float64).tiny),
        )
        return np.asarray(output * guard, dtype=np.float64)


def _future_maximum(values: np.ndarray, lookahead_frames: int) -> np.ndarray:
    """Return the maximum from each frame through its lookahead horizon."""
    if lookahead_frames <= 0:
        return values.copy()
    result = np.empty_like(values)
    candidates: deque[int] = deque()
    right = 0
    for left in range(values.size):
        limit = min(values.size, left + lookahead_frames + 1)
        while right < limit:
            while candidates and values[candidates[-1]] <= values[right]:
                candidates.pop()
            candidates.append(right)
            right += 1
        while candidates and candidates[0] < left:
            candidates.popleft()
        result[left] = values[candidates[0]]
    return result
