"""Tests for bounded, explainable reference-matching recommendations."""

import pytest

from packages.analysis_engine import AnalysisResult
from packages.reference_matching import ReferenceMatchingService, ReferenceMatchPolicy


def test_reference_matching_bounds_target_and_reuses_explicit_assistant_settings() -> None:
    policy = ReferenceMatchPolicy(maximum_target_lufs=-12.0, maximum_gain_adjustment_db=6.0)

    result = ReferenceMatchingService().match(
        _analysis(lufs=-20.0, peak_dbfs=-12.0),
        _analysis(lufs=-8.0, peak_dbfs=-3.0, centroid_hz=2_000.0),
        policy,
    )

    assert result.target_lufs == -12.0
    assert result.target_lufs_was_bounded is True
    assert result.assistant_recommendation is not None
    assert result.assistant_recommendation.decision.settings.input_gain_db == pytest.approx(6.0)
    assert result.comparison.loudness_delta_db == pytest.approx(12.0)
    assert result.comparison.spectral_centroid_ratio == pytest.approx(2.0)
    assert [finding.code for finding in result.findings] == [
        "reference_loudness",
        "reference_target_bounded",
        "reference_brighter",
    ]
    assert result.to_dict()["schema_version"] == "1.2"


def test_reference_matching_refuses_to_infer_a_target_without_reference_loudness() -> None:
    result = ReferenceMatchingService().match(
        _analysis(lufs=-20.0, peak_dbfs=-12.0),
        _analysis(lufs=None, peak_dbfs=-3.0),
    )

    assert result.target_lufs is None
    assert result.assistant_recommendation is None
    assert result.confidence == 0.2
    assert result.findings[0].code == "reference_loudness_unavailable"


def test_reference_match_policy_rejects_invalid_bounds() -> None:
    with pytest.raises(ValueError, match="must not exceed"):
        ReferenceMatchPolicy(minimum_target_lufs=-8.0, maximum_target_lufs=-20.0)


def _analysis(
    *,
    lufs: float | None,
    peak_dbfs: float,
    centroid_hz: float = 1_000.0,
) -> AnalysisResult:
    return AnalysisResult(
        duration_seconds=1.0,
        sample_rate_hz=48_000,
        bit_depth=24,
        channels=2,
        lufs=lufs,
        rms_dbfs=-18.0,
        peak_dbfs=peak_dbfs,
        true_peak_dbfs=peak_dbfs,
        dynamic_range_db=9.0,
        crest_factor_db=6.0,
        bpm=None,
        musical_key=None,
        stereo_width=0.5,
        phase_correlation=1.0,
        spectral_centroid_hz=centroid_hz,
    )
