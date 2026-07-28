"""Bounded, explainable automatic-mastering decisions."""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from pathlib import Path

from packages.analysis_engine.models import AnalysisResult
from packages.audio_core import FloatSamples, encode_wav

from .mastering import DeterministicMasteringService, MasteringResult, MasteringSettings


@dataclass(frozen=True, slots=True)
class MasteringPolicy:
    """The reproducible loudness policy used to derive render settings."""

    target_lufs: float = -14.0
    maximum_gain_adjustment_db: float = 12.0
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
        """Reject unsafe or non-deterministic policy configuration."""
        if not math.isfinite(self.target_lufs):
            raise ValueError("Target loudness must be finite")
        if (
            not math.isfinite(self.maximum_gain_adjustment_db)
            or self.maximum_gain_adjustment_db < 0.0
        ):
            raise ValueError("Maximum gain adjustment must be finite and non-negative")
        if not math.isfinite(self.ceiling_dbfs) or self.ceiling_dbfs > 0.0:
            raise ValueError("Ceiling must be finite and at or below 0 dBFS")
        if not all(
            math.isfinite(gain) and -6.0 <= gain <= 6.0
            for gain in (self.eq_low_gain_db, self.eq_mid_gain_db, self.eq_high_gain_db)
        ):
            raise ValueError("Equalizer gains must be between -6 and 6 dB")
        if not math.isfinite(self.clipper_drive_db) or not 0.0 <= self.clipper_drive_db <= 12.0:
            raise ValueError("Clipper drive must be between 0 and 12 dB")
        if (
            not math.isfinite(self.limiter_lookahead_ms)
            or not 0.0 <= self.limiter_lookahead_ms <= 10.0
        ):
            raise ValueError("Limiter lookahead must be between 0 and 10 ms")
        if (
            not math.isfinite(self.limiter_release_ms)
            or not 10.0 <= self.limiter_release_ms <= 500.0
        ):
            raise ValueError("Limiter release must be between 10 and 500 ms")
        MasteringSettings(
            high_pass_enabled=self.high_pass_enabled,
            high_pass_cutoff_hz=self.high_pass_cutoff_hz,
            dynamic_eq_center_hz=self.dynamic_eq_center_hz,
            dynamic_eq_threshold_dbfs=self.dynamic_eq_threshold_dbfs,
            dynamic_eq_reduction_db=self.dynamic_eq_reduction_db,
            bass_control_hz=self.bass_control_hz,
            bass_control_threshold_dbfs=self.bass_control_threshold_dbfs,
            bass_control_reduction_db=self.bass_control_reduction_db,
            de_esser_frequency_hz=self.de_esser_frequency_hz,
            de_esser_threshold_dbfs=self.de_esser_threshold_dbfs,
            de_esser_reduction_db=self.de_esser_reduction_db,
            saturation_amount=self.saturation_amount,
        )


@dataclass(frozen=True, slots=True)
class MasteringDecision:
    """A serializable explanation of settings derived from analysis."""

    policy: MasteringPolicy
    settings: MasteringSettings
    requested_gain_db: float | None
    gain_was_bounded: bool
    peak_headroom_gain_db: float | None
    limited_by_peak_headroom: bool
    reason: str


@dataclass(frozen=True, slots=True)
class AutomaticMasteringResult:
    """The rendered result together with its decision record."""

    render: MasteringResult
    decision: MasteringDecision
    loudness_correction_passes: int
    target_loudness_error_lu: float | None


@dataclass(frozen=True, slots=True)
class ExportedMasteringResult:
    """An automatic mastering result committed to a WAV destination."""

    mastering: AutomaticMasteringResult
    output_path: Path
    dither_applied: bool


class AutomaticMasteringService:
    """Derive bounded gain settings from analysis, then render deterministically."""

    _LOUDNESS_TOLERANCE_LU = 0.2
    _MAXIMUM_CORRECTION_PASSES = 2
    _MAXIMUM_CORRECTION_STEP_DB = 3.0
    _MAXIMUM_CONVERGENCE_GAIN_DB = 1.0
    _MINIMUM_RESPONSE_LU_PER_DB = 0.1

    def __init__(self, policy: MasteringPolicy | None = None) -> None:
        self._policy = policy or MasteringPolicy()
        self._renderer = DeterministicMasteringService()

    def decide(self, analysis: AnalysisResult) -> MasteringDecision:
        """Return an auditable gain decision without changing audio."""
        if analysis.lufs is None:
            return MasteringDecision(
                policy=self._policy,
                settings=self._settings(0.0),
                requested_gain_db=None,
                gain_was_bounded=False,
                peak_headroom_gain_db=None,
                limited_by_peak_headroom=False,
                reason="integrated loudness is unavailable; preserving input gain",
            )

        if not math.isfinite(analysis.lufs) or not math.isfinite(analysis.peak_dbfs):
            raise ValueError("Analysis loudness and peak measurements must be finite")

        requested_gain_db = self._policy.target_lufs - analysis.lufs
        policy_bounded_gain_db = max(
            -self._policy.maximum_gain_adjustment_db,
            min(self._policy.maximum_gain_adjustment_db, requested_gain_db),
        )
        peak_headroom_gain_db = self._policy.ceiling_dbfs - analysis.peak_dbfs
        # Positive loudness gain is intentionally allowed to feed the clipper and
        # true-peak limiter. Bounding it by the raw input peak prevented dense mixes
        # from ever approaching their loudness target. Downward correction remains
        # policy-bounded and the final limiter still enforces the output ceiling.
        input_gain_db = policy_bounded_gain_db
        return MasteringDecision(
            policy=self._policy,
            settings=self._settings(input_gain_db),
            requested_gain_db=requested_gain_db,
            gain_was_bounded=input_gain_db != requested_gain_db,
            peak_headroom_gain_db=peak_headroom_gain_db,
            limited_by_peak_headroom=False,
            reason="gain derived from integrated loudness; final stages enforce peak safety",
        )

    def _settings(self, input_gain_db: float) -> MasteringSettings:
        """Copy the complete explicit policy into reproducible render settings."""
        return MasteringSettings(
            input_gain_db=input_gain_db,
            ceiling_dbfs=self._policy.ceiling_dbfs,
            eq_low_gain_db=self._policy.eq_low_gain_db,
            eq_mid_gain_db=self._policy.eq_mid_gain_db,
            eq_high_gain_db=self._policy.eq_high_gain_db,
            clipper_drive_db=self._policy.clipper_drive_db,
            limiter_lookahead_ms=self._policy.limiter_lookahead_ms,
            limiter_release_ms=self._policy.limiter_release_ms,
            high_pass_enabled=self._policy.high_pass_enabled,
            high_pass_cutoff_hz=self._policy.high_pass_cutoff_hz,
            dynamic_eq_center_hz=self._policy.dynamic_eq_center_hz,
            dynamic_eq_threshold_dbfs=self._policy.dynamic_eq_threshold_dbfs,
            dynamic_eq_reduction_db=self._policy.dynamic_eq_reduction_db,
            bass_control_hz=self._policy.bass_control_hz,
            bass_control_threshold_dbfs=self._policy.bass_control_threshold_dbfs,
            bass_control_reduction_db=self._policy.bass_control_reduction_db,
            de_esser_frequency_hz=self._policy.de_esser_frequency_hz,
            de_esser_threshold_dbfs=self._policy.de_esser_threshold_dbfs,
            de_esser_reduction_db=self._policy.de_esser_reduction_db,
            saturation_amount=self._policy.saturation_amount,
        )

    def master(
        self,
        samples: FloatSamples,
        sample_rate_hz: int,
        analysis: AnalysisResult,
    ) -> AutomaticMasteringResult:
        """Decide settings from analysis and render using the deterministic chain."""
        decision = self.decide(analysis)
        render = self._renderer.master(samples, sample_rate_hz, decision.settings)
        decision, render, correction_passes = self._converge_loudness(
            samples,
            sample_rate_hz,
            decision,
            render,
        )
        target_error = (
            render.output_lufs - self._policy.target_lufs
            if render.output_lufs is not None and math.isfinite(render.output_lufs)
            else None
        )
        return AutomaticMasteringResult(
            render=render,
            decision=decision,
            loudness_correction_passes=correction_passes,
            target_loudness_error_lu=target_error,
        )

    def _converge_loudness(
        self,
        samples: FloatSamples,
        sample_rate_hz: int,
        decision: MasteringDecision,
        render: MasteringResult,
    ) -> tuple[MasteringDecision, MasteringResult, int]:
        """Accept only bounded re-renders that improve post-limiter target error."""
        if decision.requested_gain_db is None:
            return decision, render, 0
        policy_gain_limit_db = self._policy.maximum_gain_adjustment_db
        initial_gain_db = decision.settings.input_gain_db
        convergence_minimum_db = max(
            -policy_gain_limit_db,
            initial_gain_db - self._MAXIMUM_CONVERGENCE_GAIN_DB,
        )
        convergence_maximum_db = min(
            policy_gain_limit_db,
            initial_gain_db + self._MAXIMUM_CONVERGENCE_GAIN_DB,
        )
        previous_gain_db: float | None = None
        previous_output_lufs: float | None = None
        correction_passes = 0
        for _ in range(self._MAXIMUM_CORRECTION_PASSES):
            output_lufs = render.output_lufs
            if output_lufs is None or not math.isfinite(output_lufs):
                break
            error_lu = self._policy.target_lufs - output_lufs
            if abs(error_lu) <= self._LOUDNESS_TOLERANCE_LU:
                break
            current_gain_db = decision.settings.input_gain_db
            correction_db = error_lu
            if previous_gain_db is not None and previous_output_lufs is not None:
                gain_delta_db = current_gain_db - previous_gain_db
                loudness_delta_lu = output_lufs - previous_output_lufs
                if abs(gain_delta_db) > 1e-9:
                    response = loudness_delta_lu / gain_delta_db
                    if math.isfinite(response) and response >= self._MINIMUM_RESPONSE_LU_PER_DB:
                        correction_db = error_lu / response
            correction_db = max(
                -self._MAXIMUM_CORRECTION_STEP_DB,
                min(self._MAXIMUM_CORRECTION_STEP_DB, correction_db),
            )
            next_gain_db = max(
                convergence_minimum_db,
                min(convergence_maximum_db, current_gain_db + correction_db),
            )
            if abs(next_gain_db - current_gain_db) <= 1e-9:
                break
            candidate_decision = replace(
                decision,
                settings=replace(decision.settings, input_gain_db=next_gain_db),
                reason=(
                    "gain derived from integrated loudness and calibrated against "
                    "post-limiter loudness; final stages enforce peak safety"
                ),
            )
            candidate_render = self._renderer.master(
                samples,
                sample_rate_hz,
                candidate_decision.settings,
            )
            candidate_lufs = candidate_render.output_lufs
            if (
                candidate_lufs is None
                or not math.isfinite(candidate_lufs)
                or abs(self._policy.target_lufs - candidate_lufs) >= abs(error_lu)
            ):
                break
            previous_gain_db = current_gain_db
            previous_output_lufs = output_lufs
            decision = candidate_decision
            render = candidate_render
            correction_passes += 1
        return decision, render, correction_passes

    def master_to_wav(
        self,
        samples: FloatSamples,
        sample_rate_hz: int,
        analysis: AnalysisResult,
        output_path: str | Path,
        *,
        bit_depth: int = 24,
        dither: bool = True,
        overwrite: bool = False,
    ) -> ExportedMasteringResult:
        """Render an automatic master and atomically export it as PCM WAV."""
        mastering = self.master(samples, sample_rate_hz, analysis)
        written_path = encode_wav(
            output_path,
            mastering.render.samples,
            sample_rate_hz,
            bit_depth=bit_depth,
            dither=dither,
            overwrite=overwrite,
        )
        return ExportedMasteringResult(
            mastering=mastering,
            output_path=written_path,
            dither_applied=dither,
        )
