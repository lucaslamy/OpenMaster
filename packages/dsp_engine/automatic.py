"""Bounded, explainable automatic-mastering decisions."""

from __future__ import annotations

import math
from dataclasses import dataclass

from packages.analysis_engine.models import AnalysisResult
from packages.audio_core import FloatSamples

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

    settings: MasteringSettings
    requested_gain_db: float | None
    gain_was_bounded: bool
    reason: str


@dataclass(frozen=True, slots=True)
class AutomaticMasteringResult:
    """The rendered result together with its decision record."""

    render: MasteringResult
    decision: MasteringDecision


class AutomaticMasteringService:
    """Derive bounded gain settings from analysis, then render deterministically."""

    def __init__(self, policy: MasteringPolicy | None = None) -> None:
        self._policy = policy or MasteringPolicy()
        self._renderer = DeterministicMasteringService()

    def decide(self, analysis: AnalysisResult) -> MasteringDecision:
        """Return an auditable gain decision without changing audio."""
        if analysis.lufs is None:
            return MasteringDecision(
                settings=MasteringSettings(ceiling_dbfs=self._policy.ceiling_dbfs),
                requested_gain_db=None,
                gain_was_bounded=False,
                reason="integrated loudness is unavailable; preserving input gain",
            )

        requested_gain_db = self._policy.target_lufs - analysis.lufs
        input_gain_db = max(
            -self._policy.maximum_gain_adjustment_db,
            min(self._policy.maximum_gain_adjustment_db, requested_gain_db),
        )
        return MasteringDecision(
            settings=MasteringSettings(
                input_gain_db=input_gain_db,
                ceiling_dbfs=self._policy.ceiling_dbfs,
            ),
            requested_gain_db=requested_gain_db,
            gain_was_bounded=input_gain_db != requested_gain_db,
            reason="gain derived from integrated loudness against the policy target",
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
