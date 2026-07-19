"""Pure, deterministic signal measurements used by :mod:`analysis_engine`."""

import math
from typing import cast

import numpy as np
from numpy.typing import NDArray
from scipy import signal

FloatArray = NDArray[np.float64]
_EPSILON = 1e-12
_PITCH_CLASSES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
_MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
_MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.6, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def dbfs(value: float) -> float:
    """Convert a normalized linear magnitude to finite dBFS."""
    return 20.0 * math.log10(max(value, _EPSILON))


def mono_mix(samples: FloatArray) -> FloatArray:
    """Return an equal-power-independent arithmetic mono fold-down."""
    return cast(FloatArray, np.mean(samples, axis=1, dtype=np.float64))


def rms_dbfs(samples: FloatArray) -> float:
    """Calculate full-program RMS level in dBFS."""
    return dbfs(float(np.sqrt(np.mean(np.square(samples), dtype=np.float64))))


def peak_dbfs(samples: FloatArray) -> float:
    """Calculate sample peak level in dBFS."""
    return dbfs(float(np.max(np.abs(samples))))


def true_peak_dbfs(samples: FloatArray) -> float:
    """Estimate inter-sample peak using four-times polyphase oversampling."""
    oversampled = signal.resample_poly(samples, up=4, down=1, axis=0)
    return dbfs(float(np.max(np.abs(oversampled))))


def dynamic_range_db(mono: FloatArray, sample_rate: int) -> float:
    """Estimate programme dynamic range from overlapping 400 ms RMS windows."""
    window = max(1, round(sample_rate * 0.4))
    if mono.size <= window:
        return 0.0
    hop = max(1, window // 4)
    starts = np.arange(0, mono.size - window + 1, hop)
    levels = np.array(
        [dbfs(float(np.sqrt(np.mean(np.square(mono[start : start + window]))))) for start in starts]
    )
    return float(np.percentile(levels, 95) - np.percentile(levels, 10))


def spectral_centroid_hz(mono: FloatArray, sample_rate: int) -> float:
    """Calculate the magnitude-weighted mean frequency over short-time spectra."""
    frame = min(2048, mono.size)
    if frame < 2:
        return 0.0
    frequencies, _, spectrum = signal.stft(mono, fs=sample_rate, nperseg=frame, noverlap=frame // 2)
    magnitudes = np.abs(spectrum)
    weight = float(np.sum(magnitudes))
    if weight <= _EPSILON:
        return 0.0
    return float(np.sum(magnitudes * frequencies[:, np.newaxis]) / weight)


def phase_correlation(samples: FloatArray) -> float | None:
    """Return left/right Pearson correlation, when meaningful for stereo content."""
    if samples.shape[1] < 2:
        return None
    left, right = samples[:, 0], samples[:, 1]
    if np.std(left) <= _EPSILON or np.std(right) <= _EPSILON:
        return None
    return float(np.corrcoef(left, right)[0, 1])


def stereo_width(samples: FloatArray) -> float | None:
    """Return side-to-mid RMS ratio for a stereo signal; 1.0 is balanced width."""
    if samples.shape[1] < 2:
        return None
    mid = (samples[:, 0] + samples[:, 1]) * 0.5
    side = (samples[:, 0] - samples[:, 1]) * 0.5
    return float(np.sqrt(np.mean(side * side)) / max(np.sqrt(np.mean(mid * mid)), _EPSILON))


def integrated_lufs(samples: FloatArray, sample_rate: int) -> float | None:
    """Estimate BS.1770 integrated loudness with absolute and relative gating."""
    weighted = _k_weight(samples, sample_rate)
    block = round(sample_rate * 0.4)
    if weighted.shape[0] < block:
        return None
    hop = max(1, block // 4)
    starts = np.arange(0, weighted.shape[0] - block + 1, hop)
    energies = np.array(
        [np.sum(np.mean(np.square(weighted[start : start + block]), axis=0)) for start in starts]
    )
    loudness = -0.691 + 10.0 * np.log10(np.maximum(energies, _EPSILON))
    absolute = energies[loudness >= -70.0]
    if absolute.size == 0:
        return None
    ungated = -0.691 + 10.0 * math.log10(float(np.mean(absolute)))
    gated = energies[loudness >= max(-70.0, ungated - 10.0)]
    if gated.size == 0:
        return None
    return float(-0.691 + 10.0 * math.log10(float(np.mean(gated))))


def estimate_bpm(mono: FloatArray, sample_rate: int) -> float | None:
    """Estimate tempo from onset-strength autocorrelation in the 60–200 BPM range."""
    if mono.size < sample_rate * 3:
        return None
    hop, frame = 512, 2048
    _, _, spectrum = signal.stft(mono, fs=sample_rate, nperseg=frame, noverlap=frame - hop)
    flux = np.maximum(np.diff(np.abs(spectrum), axis=1), 0.0).sum(axis=0)
    flux -= np.mean(flux)
    if np.max(np.abs(flux)) <= _EPSILON:
        return None
    autocorrelation = signal.correlate(flux, flux, mode="full")[flux.size - 1 :]
    minimum_lag = max(1, round(60.0 * sample_rate / (200.0 * hop)))
    maximum_lag = min(autocorrelation.size - 1, round(60.0 * sample_rate / (60.0 * hop)))
    if maximum_lag <= minimum_lag:
        return None
    lag = minimum_lag + int(np.argmax(autocorrelation[minimum_lag : maximum_lag + 1]))
    return round(60.0 * sample_rate / (lag * hop), 2)


def estimate_key(mono: FloatArray, sample_rate: int) -> str | None:
    """Estimate major/minor key using pitch-class energy and Krumhansl profiles."""
    if mono.size < 2048 or np.max(np.abs(mono)) <= _EPSILON:
        return None
    frequencies, _, spectrum = signal.stft(mono, fs=sample_rate, nperseg=4096, noverlap=3072)
    energy = np.abs(spectrum).sum(axis=1)
    chroma = np.zeros(12)
    positive = frequencies > 0.0
    midi = np.rint(69 + 12 * np.log2(frequencies[positive] / 440.0)).astype(int)
    np.add.at(chroma, midi % 12, energy[positive])
    if chroma.sum() <= _EPSILON:
        return None
    normalized = (chroma - chroma.mean()) / max(float(chroma.std()), _EPSILON)
    candidates: list[tuple[float, str]] = []
    for root, pitch in enumerate(_PITCH_CLASSES):
        for profile, suffix in ((_MAJOR_PROFILE, "major"), (_MINOR_PROFILE, "minor")):
            target = np.roll(profile, root)
            target = (target - target.mean()) / target.std()
            candidates.append((float(np.dot(normalized, target)), f"{pitch} {suffix}"))
    return max(candidates, key=lambda item: item[0])[1]


def _k_weight(samples: FloatArray, sample_rate: int) -> FloatArray:
    """Apply the K-weighting shelf and high-pass filters for loudness measurement."""
    shelf = _high_shelf(sample_rate, frequency=1681.974, gain_db=4.0, quality=0.707)
    high_pass = signal.butter(2, 38.135 / (sample_rate / 2.0), btype="highpass", output="ba")
    filtered = signal.lfilter(*shelf, samples, axis=0)
    return cast(FloatArray, signal.lfilter(*high_pass, filtered, axis=0))


def _high_shelf(
    sample_rate: int, frequency: float, gain_db: float, quality: float
) -> tuple[FloatArray, FloatArray]:
    """Return normalized RBJ high-shelf biquad coefficients."""
    amplitude = 10.0 ** (gain_db / 40.0)
    omega = 2.0 * math.pi * frequency / sample_rate
    alpha = math.sin(omega) / (2.0 * quality)
    beta = 2.0 * math.sqrt(amplitude) * alpha
    cosine = math.cos(omega)
    b = np.array(
        [
            amplitude * ((amplitude + 1) + (amplitude - 1) * cosine + beta),
            -2 * amplitude * ((amplitude - 1) + (amplitude + 1) * cosine),
            amplitude * ((amplitude + 1) + (amplitude - 1) * cosine - beta),
        ]
    )
    a = np.array(
        [
            (amplitude + 1) - (amplitude - 1) * cosine + beta,
            2 * ((amplitude - 1) - (amplitude + 1) * cosine),
            (amplitude + 1) - (amplitude - 1) * cosine - beta,
        ]
    )
    return b / a[0], a / a[0]
