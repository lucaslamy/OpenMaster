"""Bounded, explainable automatic-mastering decisions."""

from __future__ import annotations

import math
from dataclasses import dataclass
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


@dataclass(frozen=True, slots=True)
class ExportedMasteringResult:
    """An automatic mastering result committed to a WAV destination."""

    mastering: AutomaticMasteringResult
    output_path: Path


class AutomaticMasteringService:
    """Derive bounded gain settings from analysis, then render deterministically."""

    def __init__(self, policy: MasteringPolicy | None = None) -> None:
        self._policy = policy or MasteringPolicy()
        self._renderer = DeterministicMasteringService()

    def decide(self, analysis: AnalysisResult) -> MasteringDecision:
        """Return an auditable gain decision without changing audio."""
        if analysis.lufs is None:
            return MasteringDecision(
                policy=self._policy,
                settings=MasteringSettings(ceiling_dbfs=self._policy.ceiling_dbfs),
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
        input_gain_db = max(
            -self._policy.maximum_gain_adjustment_db,
            min(policy_bounded_gain_db, peak_headroom_gain_db),
        )
        return MasteringDecision(
            policy=self._policy,
            settings=MasteringSettings(
                input_gain_db=input_gain_db,
                ceiling_dbfs=self._policy.ceiling_dbfs,
            ),
            requested_gain_db=requested_gain_db,
            gain_was_bounded=input_gain_db != requested_gain_db,
            peak_headroom_gain_db=peak_headroom_gain_db,
            limited_by_peak_headroom=input_gain_db < policy_bounded_gain_db,
            reason="gain derived from integrated loudness and constrained by peak headroom",
        )

    def master(
        self,
        samples: FloatSamples,
        sample_rate_hz: int,
        analysis: AnalysisResult,
    ) -> AutomaticMasteringResult:
        """Decide settings from analysis and render using the deterministic chain."""
        decision = self.decide(analysis)
        return AutomaticMasteringResult(
            render=self._renderer.master(samples, sample_rate_hz, decision.settings),
            decision=decision,
        )

    def master_to_wav(
        self,
        samples: FloatSamples,
        sample_rate_hz: int,
        analysis: AnalysisResult,
        output_path: str | Path,
        *,
        bit_depth: int = 24,
        overwrite: bool = False,
    ) -> ExportedMasteringResult:
        """Render an automatic master and atomically export it as PCM WAV."""
        mastering = self.master(samples, sample_rate_hz, analysis)
        written_path = encode_wav(
            output_path,
            mastering.render.samples,
            sample_rate_hz,
            bit_depth=bit_depth,
            overwrite=overwrite,
        )
        return ExportedMasteringResult(mastering=mastering, output_path=written_path)
