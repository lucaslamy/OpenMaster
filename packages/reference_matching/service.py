"""Compare analysis results and derive bounded reference-aware recommendations."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Any

from packages.analysis_engine import AnalysisResult
from packages.mastering_assistant import MasteringAssistant, MasteringRecommendation

REFERENCE_RECOMMENDATION_SCHEMA_VERSION = "1.2"


@dataclass(frozen=True, slots=True)
class ReferenceMatchPolicy:
    """Safety bounds for targets inferred from a selected reference."""

    minimum_target_lufs: float = -20.0
    maximum_target_lufs: float = -8.0
    maximum_gain_adjustment_db: float = 6.0
    ceiling_dbfs: float = -1.0

    def __post_init__(self) -> None:
        """Reject invalid or unsafe reference-match policy values."""
        values = (
            self.minimum_target_lufs,
            self.maximum_target_lufs,
            self.maximum_gain_adjustment_db,
            self.ceiling_dbfs,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("Reference-match policy values must be finite")
        if self.minimum_target_lufs > self.maximum_target_lufs:
            raise ValueError("Minimum target loudness must not exceed maximum target loudness")
        if self.maximum_gain_adjustment_db < 0.0:
            raise ValueError("Maximum gain adjustment must be non-negative")
        if self.ceiling_dbfs > 0.0:
            raise ValueError("Ceiling must be at or below 0 dBFS")


@dataclass(frozen=True, slots=True)
class ReferenceComparison:
    """Measurement deltas between an input and the selected reference."""

    loudness_delta_db: float | None
    dynamic_range_delta_db: float
    spectral_centroid_ratio: float | None
    stereo_width_delta: float | None
    phase_correlation_delta: float | None


@dataclass(frozen=True, slots=True)
class ReferenceMatchFinding:
    """One reviewable explanation derived from the input/reference comparison."""

    code: str
    message: str


@dataclass(frozen=True, slots=True)
class ReferenceMatchRecommendation:
    """A fully serialized, bounded reference-match recommendation."""

    policy: ReferenceMatchPolicy
    comparison: ReferenceComparison
    target_lufs: float | None
    target_lufs_was_bounded: bool
    assistant_recommendation: MasteringRecommendation | None
    confidence: float
    findings: tuple[ReferenceMatchFinding, ...]

    def to_dict(self) -> dict[str, Any]:
        """Return a versioned JSON-ready representation for automation boundaries."""
        return {"schema_version": REFERENCE_RECOMMENDATION_SCHEMA_VERSION, **asdict(self)}


class ReferenceMatchingService:
    """Derive transparent mastering advice by comparing immutable analysis results."""

    def match(
        self,
        input_analysis: AnalysisResult,
        reference_analysis: AnalysisResult,
        policy: ReferenceMatchPolicy | None = None,
    ) -> ReferenceMatchRecommendation:
        """Return bounded loudness advice and non-destructive comparison findings."""
        effective_policy = policy or ReferenceMatchPolicy()
        comparison = _compare(input_analysis, reference_analysis)
        if reference_analysis.lufs is None:
            return ReferenceMatchRecommendation(
                policy=effective_policy,
                comparison=comparison,
                target_lufs=None,
                target_lufs_was_bounded=False,
                assistant_recommendation=None,
                confidence=0.20,
                findings=(
                    ReferenceMatchFinding(
                        "reference_loudness_unavailable",
                        "Reference integrated loudness is unavailable; no matching "
                        "policy is proposed.",
                    ),
                ),
            )

        target_lufs = min(
            effective_policy.maximum_target_lufs,
            max(effective_policy.minimum_target_lufs, reference_analysis.lufs),
        )
        target_lufs_was_bounded = target_lufs != reference_analysis.lufs
        assistant = MasteringAssistant().recommend(
            input_analysis,
            target_lufs=target_lufs,
            maximum_gain_adjustment_db=effective_policy.maximum_gain_adjustment_db,
            ceiling_dbfs=effective_policy.ceiling_dbfs,
        )
        findings = [
            ReferenceMatchFinding(
                "reference_loudness",
                (
                    f"Reference loudness is {reference_analysis.lufs:.1f} LUFS; "
                    f"the bounded matching target is {target_lufs:.1f} LUFS."
                ),
            )
        ]
        if target_lufs_was_bounded:
            findings.append(
                ReferenceMatchFinding(
                    "reference_target_bounded",
                    "Reference loudness is outside the configured safe target range.",
                )
            )
        findings.extend(_comparison_findings(comparison))
        confidence = assistant.confidence
        if comparison.spectral_centroid_ratio is None:
            confidence -= 0.10
        if comparison.stereo_width_delta is None or comparison.phase_correlation_delta is None:
            confidence -= 0.10
        return ReferenceMatchRecommendation(
            policy=effective_policy,
            comparison=comparison,
            target_lufs=target_lufs,
            target_lufs_was_bounded=target_lufs_was_bounded,
            assistant_recommendation=assistant,
            confidence=round(max(0.20, confidence), 2),
            findings=tuple(findings),
        )


def _compare(
    input_analysis: AnalysisResult, reference_analysis: AnalysisResult
) -> ReferenceComparison:
    """Calculate stable measurement deltas without inferring hidden DSP settings."""
    loudness_delta = (
        None
        if input_analysis.lufs is None or reference_analysis.lufs is None
        else reference_analysis.lufs - input_analysis.lufs
    )
    spectral_ratio = _positive_ratio(
        reference_analysis.spectral_centroid_hz, input_analysis.spectral_centroid_hz
    )
    stereo_delta = _optional_delta(reference_analysis.stereo_width, input_analysis.stereo_width)
    phase_delta = _optional_delta(
        reference_analysis.phase_correlation, input_analysis.phase_correlation
    )
    return ReferenceComparison(
        loudness_delta_db=loudness_delta,
        dynamic_range_delta_db=(
            reference_analysis.dynamic_range_db - input_analysis.dynamic_range_db
        ),
        spectral_centroid_ratio=spectral_ratio,
        stereo_width_delta=stereo_delta,
        phase_correlation_delta=phase_delta,
    )


def _positive_ratio(numerator: float, denominator: float) -> float | None:
    """Return a finite positive ratio, or no comparison for unusable measurements."""
    if not math.isfinite(numerator) or not math.isfinite(denominator) or denominator <= 0.0:
        return None
    return numerator / denominator


def _optional_delta(reference: float | None, input_value: float | None) -> float | None:
    """Return an optional metric delta only when both measurements are present."""
    if reference is None or input_value is None:
        return None
    return reference - input_value


def _comparison_findings(comparison: ReferenceComparison) -> list[ReferenceMatchFinding]:
    """Describe meaningful deltas while leaving all non-gain DSP choices to the user."""
    findings: list[ReferenceMatchFinding] = []
    if comparison.spectral_centroid_ratio is not None and comparison.spectral_centroid_ratio > 1.25:
        findings.append(
            ReferenceMatchFinding(
                "reference_brighter",
                "Reference spectral centroid is materially higher; review EQ manually "
                "before matching.",
            )
        )
    elif (
        comparison.spectral_centroid_ratio is not None and comparison.spectral_centroid_ratio < 0.80
    ):
        findings.append(
            ReferenceMatchFinding(
                "reference_darker",
                "Reference spectral centroid is materially lower; review EQ manually "
                "before matching.",
            )
        )
    if comparison.stereo_width_delta is not None and abs(comparison.stereo_width_delta) > 0.15:
        findings.append(
            ReferenceMatchFinding(
                "stereo_difference",
                "Stereo-width difference was measured; no stereo adjustment is applied "
                "automatically.",
            )
        )
    return findings
