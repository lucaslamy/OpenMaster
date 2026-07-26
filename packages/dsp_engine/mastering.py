"""Traceable deterministic mastering orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from packages.analysis_engine.metrics import integrated_lufs, true_peak_dbfs
from packages.audio_core import FloatSamples

from .clipper import OversampledClipperProcessor
from .equalizer import TonalEqualizerProcessor
from .gain import GainProcessor
from .limiter import LimiterProcessor
from .pipeline import DspPipeline
from .saturation import SaturationProcessor
from .spectral_dynamics import (
    BassControlProcessor,
    DeEsserProcessor,
    DynamicEqualizerProcessor,
    HighPassProcessor,
)


@dataclass(frozen=True, slots=True)
class MasteringSettings:
    """Explicit, reproducible settings for the initial mastering workflow."""

    input_gain_db: float = 0.0
    ceiling_dbfs: float = -1.0
    eq_low_gain_db: float = 0.0
    eq_mid_gain_db: float = 0.0
    eq_high_gain_db: float = 0.0
    clipper_drive_db: float = 0.0
    limiter_lookahead_ms: float = 3.0
    limiter_release_ms: float = 80.0
    high_pass_enabled: bool = True
    high_pass_cutoff_hz: float = 25.0
    dynamic_eq_center_hz: float = 2_500.0
    dynamic_eq_threshold_dbfs: float = -18.0
    dynamic_eq_reduction_db: float = 0.0
    bass_control_hz: float = 140.0
    bass_control_threshold_dbfs: float = -16.0
    bass_control_reduction_db: float = 0.0
    de_esser_frequency_hz: float = 7_000.0
    de_esser_threshold_dbfs: float = -22.0
    de_esser_reduction_db: float = 0.0
    saturation_amount: float = 0.0

    def __post_init__(self) -> None:
        """Validate the frequency-selective stages when settings are created."""
        HighPassProcessor(self.high_pass_cutoff_hz, self.high_pass_enabled)
        DynamicEqualizerProcessor(
            center_hz=self.dynamic_eq_center_hz,
            threshold_dbfs=self.dynamic_eq_threshold_dbfs,
            maximum_reduction_db=self.dynamic_eq_reduction_db,
        )
        BassControlProcessor(
            crossover_hz=self.bass_control_hz,
            threshold_dbfs=self.bass_control_threshold_dbfs,
            maximum_reduction_db=self.bass_control_reduction_db,
        )
        DeEsserProcessor(
            center_hz=self.de_esser_frequency_hz,
            threshold_dbfs=self.de_esser_threshold_dbfs,
            maximum_reduction_db=self.de_esser_reduction_db,
        )
        SaturationProcessor(self.saturation_amount)


@dataclass(frozen=True, slots=True)
class MasteringResult:
    """Rendered audio and the ordered processors that transformed it."""

    samples: FloatSamples
    applied_processors: tuple[str, ...]
    output_lufs: float | None
    output_true_peak_dbfs: float


class DeterministicMasteringService:
    """Render the v1.0 mastering baseline from explicit settings only."""

    def master(
        self,
        samples: FloatSamples,
        sample_rate_hz: int,
        settings: MasteringSettings,
    ) -> MasteringResult:
        """Apply the complete deterministic mastering chain in auditable order."""
        pipeline = DspPipeline(
            (
                HighPassProcessor(
                    cutoff_hz=settings.high_pass_cutoff_hz,
                    enabled=settings.high_pass_enabled,
                ),
                TonalEqualizerProcessor(
                    settings.eq_low_gain_db,
                    settings.eq_mid_gain_db,
                    settings.eq_high_gain_db,
                ),
                DynamicEqualizerProcessor(
                    center_hz=settings.dynamic_eq_center_hz,
                    threshold_dbfs=settings.dynamic_eq_threshold_dbfs,
                    maximum_reduction_db=settings.dynamic_eq_reduction_db,
                ),
                BassControlProcessor(
                    crossover_hz=settings.bass_control_hz,
                    threshold_dbfs=settings.bass_control_threshold_dbfs,
                    maximum_reduction_db=settings.bass_control_reduction_db,
                ),
                DeEsserProcessor(
                    center_hz=settings.de_esser_frequency_hz,
                    threshold_dbfs=settings.de_esser_threshold_dbfs,
                    maximum_reduction_db=settings.de_esser_reduction_db,
                ),
                GainProcessor(settings.input_gain_db),
                SaturationProcessor(settings.saturation_amount),
                OversampledClipperProcessor(settings.clipper_drive_db),
                LimiterProcessor(
                    settings.ceiling_dbfs,
                    settings.limiter_lookahead_ms,
                    settings.limiter_release_ms,
                ),
            )
        )
        rendered = pipeline.process(samples, sample_rate_hz)
        return MasteringResult(
            samples=rendered,
            applied_processors=(
                "high_pass",
                "three_band_equalizer",
                "dynamic_equalizer",
                "bass_control",
                "de_esser",
                "gain",
                "saturation",
                "oversampled_clipper",
                "true_peak_limiter",
            ),
            output_lufs=integrated_lufs(rendered, sample_rate_hz),
            output_true_peak_dbfs=true_peak_dbfs(rendered),
        )
