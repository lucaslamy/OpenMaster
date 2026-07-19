"""Application service that coordinates deterministic audio analysis."""

from pathlib import Path

from packages.audio_core import DecodedAudio, decode_audio

from .metrics import (
    dynamic_range_db,
    estimate_bpm,
    estimate_key,
    integrated_lufs,
    mono_mix,
    peak_dbfs,
    phase_correlation,
    rms_dbfs,
    spectral_centroid_hz,
    stereo_width,
    true_peak_dbfs,
)
from .models import AnalysisResult


class AnalysisService:
    """Analyse supported audio files using a deterministic, local CPU pipeline."""

    def analyze(self, path: str | Path) -> AnalysisResult:
        """Validate and analyse one audio file, returning all available v0.7 measurements."""
        return self.analyze_decoded(decode_audio(path))

    def analyze_decoded(self, decoded: DecodedAudio) -> AnalysisResult:
        """Analyse a decoded stream without repeating input decoding and validation."""
        samples = decoded.samples
        metadata = decoded.metadata
        sample_rate = metadata.sample_rate_hz
        mono = mono_mix(samples)
        rms = rms_dbfs(samples)
        peak = peak_dbfs(samples)
        return AnalysisResult(
            duration_seconds=metadata.duration_seconds,
            sample_rate_hz=sample_rate,
            bit_depth=metadata.bit_depth,
            channels=metadata.channels,
            lufs=integrated_lufs(samples, sample_rate),
            rms_dbfs=rms,
            peak_dbfs=peak,
            true_peak_dbfs=true_peak_dbfs(samples),
            dynamic_range_db=dynamic_range_db(mono, sample_rate),
            crest_factor_db=peak - rms,
            bpm=estimate_bpm(mono, sample_rate),
            musical_key=estimate_key(mono, sample_rate),
            stereo_width=stereo_width(samples),
            phase_correlation=phase_correlation(samples),
            spectral_centroid_hz=spectral_centroid_hz(mono, sample_rate),
        )
