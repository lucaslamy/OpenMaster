"""Traceable deterministic mastering orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from packages.audio_core import FloatSamples

from .gain import GainProcessor
from .limiter import LimiterProcessor
from .pipeline import DspPipeline


@dataclass(frozen=True, slots=True)
class MasteringSettings:
    """Explicit, reproducible settings for the initial mastering workflow."""

    input_gain_db: float = 0.0
    ceiling_dbfs: float = -1.0


@dataclass(frozen=True, slots=True)
class MasteringResult:
    """Rendered audio and the ordered processors that transformed it."""

    samples: FloatSamples
    applied_processors: tuple[str, ...]


class DeterministicMasteringService:
    """Render the v1.0 mastering baseline from explicit settings only."""

    def master(
        self,
        samples: FloatSamples,
        sample_rate_hz: int,
        settings: MasteringSettings,
    ) -> MasteringResult:
        """Apply gain staging followed by linked sample-peak protection."""
        pipeline = DspPipeline(
            (
                GainProcessor(settings.input_gain_db),
                LimiterProcessor(settings.ceiling_dbfs),
            )
        )
        return MasteringResult(
            samples=pipeline.process(samples, sample_rate_hz),
            applied_processors=("gain", "sample_peak_limiter"),
        )
