"""Deterministic filters and frequency-selective dynamics for mastering."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import cast

import numpy as np
from scipy.signal import butter, sosfilt, sosfiltfilt

from packages.audio_core import FloatSamples

from .gain import _validate_audio


@dataclass(frozen=True, slots=True)
class HighPassProcessor:
    """Remove subsonic energy with a fourth-order Butterworth high-pass."""

    cutoff_hz: float = 25.0
    enabled: bool = True

    def __post_init__(self) -> None:
        """Restrict the cutoff to the useful mastering range."""
        if not math.isfinite(self.cutoff_hz) or not 15.0 <= self.cutoff_hz <= 80.0:
            raise ValueError("High-pass cutoff must be between 15 and 80 Hz")

    def process(self, samples: FloatSamples, sample_rate_hz: int) -> FloatSamples:
        """Apply a stable 24 dB/octave high-pass, or return a clean bypass."""
        _validate_audio(samples, sample_rate_hz)
        if not self.enabled:
            return np.asarray(samples, dtype=np.float64).copy()
        cutoff_hz = min(self.cutoff_hz, sample_rate_hz * 0.45)
        sections = butter(4, cutoff_hz, btype="highpass", fs=sample_rate_hz, output="sos")
        return np.asarray(sosfilt(sections, samples, axis=0), dtype=np.float64)


@dataclass(frozen=True, slots=True)
class DynamicEqualizerProcessor:
    """Tame excessive energy in one band using a linked envelope."""

    center_hz: float = 2_500.0
    quality_factor: float = 1.0
    threshold_dbfs: float = -18.0
    maximum_reduction_db: float = 0.0

    def __post_init__(self) -> None:
        """Keep the dynamic correction conservative and reproducible."""
        if not math.isfinite(self.center_hz) or not 80.0 <= self.center_hz <= 12_000.0:
            raise ValueError("Dynamic EQ center frequency must be between 80 and 12000 Hz")
        if not math.isfinite(self.quality_factor) or not 0.3 <= self.quality_factor <= 8.0:
            raise ValueError("Dynamic EQ Q must be between 0.3 and 8")
        if not math.isfinite(self.threshold_dbfs) or not -60.0 <= self.threshold_dbfs <= 0.0:
            raise ValueError("Dynamic EQ threshold must be between -60 and 0 dBFS")
        if (
            not math.isfinite(self.maximum_reduction_db)
            or not 0.0 <= self.maximum_reduction_db <= 12.0
        ):
            raise ValueError("Dynamic EQ reduction must be between 0 and 12 dB")

    def process(self, samples: FloatSamples, sample_rate_hz: int) -> FloatSamples:
        """Reduce only the selected band when its linked level crosses threshold."""
        _validate_audio(samples, sample_rate_hz)
        if self.maximum_reduction_db == 0.0:
            return np.asarray(samples, dtype=np.float64).copy()
        low_hz, high_hz = _band_edges(self.center_hz, self.quality_factor, sample_rate_hz)
        band = _filtered(samples, sample_rate_hz, (low_hz, high_hz), "bandpass")
        reduction_db = _linked_reduction_db(
            band,
            sample_rate_hz,
            self.threshold_dbfs,
            self.maximum_reduction_db,
            ratio=2.0,
            attack_ms=12.0,
            release_ms=120.0,
        )
        gain = 10.0 ** (-reduction_db[:, np.newaxis] / 20.0)
        return np.asarray(samples + band * (gain - 1.0), dtype=np.float64)


@dataclass(frozen=True, slots=True)
class BassControlProcessor:
    """Control intermittent low-frequency excess without flattening the mix."""

    crossover_hz: float = 140.0
    threshold_dbfs: float = -16.0
    maximum_reduction_db: float = 0.0

    def __post_init__(self) -> None:
        """Validate a deliberately narrow set of mastering-safe controls."""
        if not math.isfinite(self.crossover_hz) or not 60.0 <= self.crossover_hz <= 300.0:
            raise ValueError("Bass crossover must be between 60 and 300 Hz")
        if not math.isfinite(self.threshold_dbfs) or not -60.0 <= self.threshold_dbfs <= 0.0:
            raise ValueError("Bass threshold must be between -60 and 0 dBFS")
        if (
            not math.isfinite(self.maximum_reduction_db)
            or not 0.0 <= self.maximum_reduction_db <= 12.0
        ):
            raise ValueError("Bass reduction must be between 0 and 12 dB")

    def process(self, samples: FloatSamples, sample_rate_hz: int) -> FloatSamples:
        """Compress the linked low band and preserve all higher frequencies."""
        _validate_audio(samples, sample_rate_hz)
        if self.maximum_reduction_db == 0.0:
            return np.asarray(samples, dtype=np.float64).copy()
        bass = _filtered(
            samples,
            sample_rate_hz,
            min(self.crossover_hz, sample_rate_hz * 0.45),
            "lowpass",
        )
        reduction_db = _linked_reduction_db(
            bass,
            sample_rate_hz,
            self.threshold_dbfs,
            self.maximum_reduction_db,
            ratio=3.0,
            attack_ms=25.0,
            release_ms=180.0,
        )
        gain = 10.0 ** (-reduction_db[:, np.newaxis] / 20.0)
        return np.asarray(samples + bass * (gain - 1.0), dtype=np.float64)


@dataclass(frozen=True, slots=True)
class DeEsserProcessor:
    """Reduce linked sibilant-band bursts while preserving stereo balance."""

    center_hz: float = 7_000.0
    threshold_dbfs: float = -22.0
    maximum_reduction_db: float = 0.0

    def __post_init__(self) -> None:
        """Constrain the detector to common vocal sibilance frequencies."""
        if not math.isfinite(self.center_hz) or not 3_000.0 <= self.center_hz <= 12_000.0:
            raise ValueError("De-esser frequency must be between 3000 and 12000 Hz")
        if not math.isfinite(self.threshold_dbfs) or not -60.0 <= self.threshold_dbfs <= 0.0:
            raise ValueError("De-esser threshold must be between -60 and 0 dBFS")
        if (
            not math.isfinite(self.maximum_reduction_db)
            or not 0.0 <= self.maximum_reduction_db <= 12.0
        ):
            raise ValueError("De-esser reduction must be between 0 and 12 dB")

    def process(self, samples: FloatSamples, sample_rate_hz: int) -> FloatSamples:
        """Attenuate short sibilant events through frequency-selective compression."""
        _validate_audio(samples, sample_rate_hz)
        if self.maximum_reduction_db == 0.0:
            return np.asarray(samples, dtype=np.float64).copy()
        low_hz, high_hz = _band_edges(self.center_hz, 1.4, sample_rate_hz)
        sibilance = _filtered(samples, sample_rate_hz, (low_hz, high_hz), "bandpass")
        reduction_db = _linked_reduction_db(
            sibilance,
            sample_rate_hz,
            self.threshold_dbfs,
            self.maximum_reduction_db,
            ratio=4.0,
            attack_ms=2.0,
            release_ms=70.0,
        )
        gain = 10.0 ** (-reduction_db[:, np.newaxis] / 20.0)
        return np.asarray(samples + sibilance * (gain - 1.0), dtype=np.float64)


def _band_edges(
    center_hz: float, quality_factor: float, sample_rate_hz: int
) -> tuple[float, float]:
    """Convert center/Q controls into valid octave-symmetric band edges."""
    octave_width = 1.0 / quality_factor
    ratio = 2.0 ** (octave_width / 2.0)
    return max(20.0, center_hz / ratio), min(sample_rate_hz * 0.48, center_hz * ratio)


def _filtered(
    samples: FloatSamples,
    sample_rate_hz: int,
    cutoff_hz: float | tuple[float, float],
    kind: str,
) -> FloatSamples:
    """Return a fourth-order frequency band used by a selective processor."""
    sections = butter(4, cutoff_hz, btype=kind, fs=sample_rate_hz, output="sos")
    if samples.shape[0] <= 15:
        return np.asarray(sosfilt(sections, samples, axis=0), dtype=np.float64)
    return np.asarray(sosfiltfilt(sections, samples, axis=0), dtype=np.float64)


def _linked_reduction_db(
    band: FloatSamples,
    sample_rate_hz: int,
    threshold_dbfs: float,
    maximum_reduction_db: float,
    *,
    ratio: float,
    attack_ms: float,
    release_ms: float,
) -> np.ndarray:
    """Return a channel-linked, attack/release-smoothed reduction envelope."""
    detector_db = 20.0 * np.log10(np.maximum(np.max(np.abs(band), axis=1), 1e-12))
    target = np.minimum(
        maximum_reduction_db,
        np.maximum(0.0, detector_db - threshold_dbfs) * (1.0 - 1.0 / ratio),
    )
    attack = math.exp(-1.0 / (sample_rate_hz * attack_ms / 1_000.0))
    release = math.exp(-1.0 / (sample_rate_hz * release_ms / 1_000.0))
    smoothed = np.empty_like(target)
    state = 0.0
    for index, value in enumerate(target):
        coefficient = attack if value > state else release
        state = coefficient * state + (1.0 - coefficient) * value
        smoothed[index] = state
    return cast(np.ndarray, smoothed)
