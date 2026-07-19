"""Typed public result models for audio analysis."""

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """Audio metadata and signal measurements produced by an analysis run."""

    duration_seconds: float
    sample_rate_hz: int
    bit_depth: int
    channels: int
    lufs: float | None
    rms_dbfs: float
    peak_dbfs: float
    true_peak_dbfs: float
    dynamic_range_db: float
    crest_factor_db: float
    bpm: float | None
    musical_key: str | None
    stereo_width: float | None
    phase_correlation: float | None
    spectral_centroid_hz: float

    def to_dict(self) -> dict[str, Any]:
        """Return a serializable representation suitable for application boundaries."""
        return asdict(self)
