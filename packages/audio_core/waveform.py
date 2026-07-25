"""Compact waveform envelopes for durable browser comparison views."""

from __future__ import annotations

import numpy as np

from .models import FloatSamples


def waveform_envelope(samples: FloatSamples, *, points: int = 256) -> list[float]:
    """Return bounded mono peak magnitudes without retaining full audio in JSON."""
    if points < 16 or points > 2048:
        raise ValueError("Waveform points must be between 16 and 2048")
    mono = np.max(np.abs(samples), axis=1)
    if mono.size == 0:
        return [0.0] * points
    edges = np.linspace(0, mono.size, points + 1, dtype=np.int64)
    envelope = [
        float(np.max(mono[edges[index] : max(edges[index] + 1, edges[index + 1])]))
        for index in range(points)
    ]
    peak = max(envelope, default=0.0)
    if peak <= 0.0:
        return [0.0] * points
    return [round(value / peak, 4) for value in envelope]
