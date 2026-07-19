"""Deterministic, explainable mastering recommendations from analysis measurements."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from packages.analysis_engine import AnalysisResult
from packages.dsp_engine import AutomaticMasteringService, MasteringDecision, MasteringPolicy

RECOMMENDATION_SCHEMA_VERSION = "1.1"


@dataclass(frozen=True, slots=True)
class AssistantFinding:
    """One human-readable reason supporting a mastering recommendation."""

    code: str
    message: str


@dataclass(frozen=True, slots=True)
class MasteringRecommendation:
    """A complete, serializable recommendation with no implicit DSP settings."""

    decision: MasteringDecision
    confidence: float
    findings: tuple[AssistantFinding, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-ready recommendation including all effective settings."""
        return {"schema_version": RECOMMENDATION_SCHEMA_VERSION, **asdict(self)}


class MasteringAssistant:
    """Recommend explicit automatic-mastering settings from immutable analysis data."""

    def recommend(
        self,
        analysis: AnalysisResult,
        *,
        target_lufs: float = -14.0,
        maximum_gain_adjustment_db: float = 12.0,
        ceiling_dbfs: float = -1.0,
    ) -> MasteringRecommendation:
        """Build a bounded policy, decision trace, confidence score, and findings.

        Confidence is intentionally deterministic: it starts at 0.95, loses 0.15
        when gain is peak-limited, 0.10 when stereo evidence is unavailable, and is
        fixed to 0.20 when integrated loudness is unavailable.
        """
        policy = MasteringPolicy(
            target_lufs=target_lufs,
            maximum_gain_adjustment_db=maximum_gain_adjustment_db,
            ceiling_dbfs=ceiling_dbfs,
        )
        decision = AutomaticMasteringService(policy).decide(analysis)
        if analysis.lufs is None:
            return MasteringRecommendation(
                decision=decision,
                confidence=0.20,
                findings=(
                    AssistantFinding(
                        "loudness_unavailable",
                        "Integrated loudness is unavailable, so the assistant preserves "
                        "input gain.",
                    ),
                ),
            )

        findings = [
            AssistantFinding(
                "loudness_target",
                (
                    f"Integrated loudness is {analysis.lufs:.1f} LUFS; "
                    f"the requested target is {policy.target_lufs:.1f} LUFS."
                ),
            )
        ]
        confidence = 0.95
        if decision.gain_was_bounded:
            findings.append(
                AssistantFinding(
                    "gain_bounded",
                    (
                        f"The requested {decision.requested_gain_db:.1f} dB gain is bounded to "
                        f"{decision.settings.input_gain_db:.1f} dB by the active safety policy."
                    ),
                )
            )
        if decision.limited_by_peak_headroom:
            confidence -= 0.15
            findings.append(
                AssistantFinding(
                    "peak_headroom_limited",
                    (
                        f"Measured peak headroom permits only "
                        f"{decision.peak_headroom_gain_db:.1f} dB of gain before the ceiling."
                    ),
                )
            )
        if analysis.stereo_width is None or analysis.phase_correlation is None:
            confidence -= 0.10
            findings.append(
                AssistantFinding(
                    "stereo_evidence_unavailable",
                    "Stereo measurements are unavailable; no stereo-processing "
                    "recommendation is made.",
                )
            )
        elif analysis.phase_correlation < 0.0:
            findings.append(
                AssistantFinding(
                    "phase_warning",
                    "Negative phase correlation was measured; preserve stereo width "
                    "until reviewed.",
                )
            )
        return MasteringRecommendation(
            decision=decision,
            confidence=round(max(0.20, confidence), 2),
            findings=tuple(findings),
        )
