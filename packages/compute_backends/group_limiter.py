"""CPU and optional CuPy backends for balance-preserving group limiting."""

from __future__ import annotations

import importlib
from typing import Any, Protocol

import numpy as np

from packages.audio_core import FloatSamples


class BackendUnavailableError(RuntimeError):
    """Raised when an explicitly requested optional compute backend is unavailable."""


class ComputeBackend(Protocol):
    """Compute the same shared gain/limiter operation on a selected device."""

    name: str

    def render_group(
        self,
        stems: tuple[FloatSamples, ...],
        *,
        gain: float,
        ceiling: float,
    ) -> tuple[FloatSamples, ...]:
        """Return stems scaled by one shared group limiter envelope."""


class NumpyComputeBackend:
    """Canonical deterministic CPU implementation used as the DSP reference."""

    name = "cpu"

    def render_group(
        self,
        stems: tuple[FloatSamples, ...],
        *,
        gain: float,
        ceiling: float,
    ) -> tuple[FloatSamples, ...]:
        """Apply a shared gain and limiter envelope with NumPy float64 operations."""
        gained_stems = tuple(samples * gain for samples in stems)
        group_mix = np.sum(gained_stems, axis=0, dtype=np.float64)
        frame_peaks = np.max(np.abs(group_mix), axis=1, keepdims=True)
        group_gains = np.minimum(
            1.0,
            ceiling / np.maximum(frame_peaks, np.finfo(np.float64).tiny),
        )
        return tuple(
            np.asarray(samples * group_gains, dtype=np.float64) for samples in gained_stems
        )


class CupyComputeBackend:
    """Optional GPU implementation with the same public operation as the CPU backend."""

    name = "gpu"

    def __init__(self) -> None:
        """Load CuPy only when the caller explicitly requests GPU execution."""
        try:
            self._cupy: Any = importlib.import_module("cupy")
        except ImportError as error:
            raise BackendUnavailableError(
                "GPU backend requires the optional 'cupy' package"
            ) from error

    def render_group(
        self,
        stems: tuple[FloatSamples, ...],
        *,
        gain: float,
        ceiling: float,
    ) -> tuple[FloatSamples, ...]:
        """Apply the group operation on CuPy arrays and return validated NumPy buffers."""
        cupy = self._cupy
        device_stems = tuple(cupy.asarray(samples, dtype=cupy.float64) * gain for samples in stems)
        group_mix = cupy.sum(cupy.stack(device_stems), axis=0, dtype=cupy.float64)
        frame_peaks = cupy.max(cupy.abs(group_mix), axis=1, keepdims=True)
        group_gains = cupy.minimum(
            1.0,
            ceiling / cupy.maximum(frame_peaks, cupy.finfo(cupy.float64).tiny),
        )
        return tuple(
            np.asarray(cupy.asnumpy(samples * group_gains), dtype=np.float64)
            for samples in device_stems
        )


def resolve_compute_backend(name: str = "cpu") -> ComputeBackend:
    """Return an explicit backend; no implicit GPU fallback can change a render."""
    if name == "cpu":
        return NumpyComputeBackend()
    if name == "gpu":
        return CupyComputeBackend()
    raise ValueError("Compute backend must be 'cpu' or 'gpu'")
