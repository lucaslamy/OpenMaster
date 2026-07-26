"""Compact truthful signal summaries for durable browser visualizations."""

from __future__ import annotations

import math

import numpy as np
from scipy import signal

from .models import FloatSamples

_EPSILON = np.finfo(np.float64).tiny


def spectral_profile(
    samples: FloatSamples,
    sample_rate_hz: int,
    *,
    points: int = 96,
) -> list[float]:
    """Return log-frequency RMS magnitude mapped from -100..0 dBFS to 0..1."""
    _validate(samples, sample_rate_hz, points)
    mono = np.asarray(np.mean(samples, axis=1, dtype=np.float64), dtype=np.float64).reshape(-1)
    if not np.any(mono):
        return [0.0] * points
    segment = min(8192, mono.size)
    frequencies_raw, power_raw = signal.welch(
        mono,
        fs=sample_rate_hz,
        nperseg=segment,
        noverlap=segment // 2,
        scaling="spectrum",
    )
    frequencies = np.asarray(frequencies_raw, dtype=np.float64)
    power = np.asarray(power_raw, dtype=np.float64)
    magnitudes_dbfs = 10.0 * np.log10(np.maximum(power, _EPSILON))
    maximum_frequency = min(20_000.0, sample_rate_hz * 0.49)
    minimum_frequency = min(40.0, maximum_frequency)
    targets = np.geomspace(minimum_frequency, maximum_frequency, points)
    interpolated = np.interp(targets, frequencies, magnitudes_dbfs)
    normalized = np.round(np.clip((interpolated + 100.0) / 100.0, 0.0, 1.0), 6)
    return [float(value) for value in normalized]


def level_timeline(samples: FloatSamples, *, points: int = 96) -> list[float]:
    """Return fixed-time RMS windows mapped from -60..0 dBFS to 0..1."""
    _validate(samples, 1, points)
    mono = np.asarray(np.mean(samples, axis=1, dtype=np.float64), dtype=np.float64).reshape(-1)
    boundaries = [round(index * mono.size / points) for index in range(points + 1)]
    levels: list[float] = []
    for index in range(points):
        window = mono[boundaries[index] : boundaries[index + 1]]
        rms = float(np.sqrt(np.mean(np.square(window)))) if window.size else 0.0
        dbfs = 20.0 * math.log10(max(rms, float(_EPSILON)))
        levels.append(round(float(np.clip((dbfs + 60.0) / 60.0, 0.0, 1.0)), 6))
    return levels


def _validate(samples: FloatSamples, sample_rate_hz: int, points: int) -> None:
    """Validate bounded visualization inputs."""
    if samples.ndim != 2 or samples.shape[0] < 1 or samples.shape[1] < 1:
        raise ValueError("Audio samples must have shape (frames, channels)")
    if sample_rate_hz < 1 or not np.isfinite(samples).all():
        raise ValueError("Audio samples and sample rate must be finite and positive")
    if not 16 <= points <= 512:
        raise ValueError("Visualization size must be between 16 and 512 points")
