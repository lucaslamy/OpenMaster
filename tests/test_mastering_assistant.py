"""Tests for explainable deterministic mastering recommendations."""

import pytest

from packages.analysis_engine import AnalysisResult
from packages.mastering_assistant import MasteringAssistant


def test_assistant_returns_serialized_policy_and_peak_limited_reasoning() -> None:
    recommendation = MasteringAssistant().recommend(_analysis(lufs=-30.0, peak_dbfs=-3.0))

    assert recommendation.decision.policy.target_lufs == -14.0
    assert recommendation.decision.settings.input_gain_db == pytest.approx(2.0)
    assert recommendation.confidence == 0.8
    assert [finding.code for finding in recommendation.findings] == [
        "loudness_target",
        "gain_bounded",
        "peak_headroom_limited",
    ]
    assert recommendation.to_dict()["decision"]["policy"]["ceiling_dbfs"] == -1.0


def test_assistant_reports_low_confidence_when_loudness_is_unavailable() -> None:
    recommendation = MasteringAssistant().recommend(_analysis(lufs=None, peak_dbfs=-3.0))

    assert recommendation.confidence == 0.2
    assert recommendation.decision.settings.input_gain_db == 0.0
    assert recommendation.findings[0].code == "loudness_unavailable"


def test_assistant_warns_about_negative_phase_without_hidden_stereo_change() -> None:
    recommendation = MasteringAssistant().recommend(
        _analysis(lufs=-18.0, peak_dbfs=-12.0, phase_correlation=-0.2)
    )

    assert recommendation.decision.settings.input_gain_db == pytest.approx(4.0)
    assert recommendation.confidence == 0.95
    assert recommendation.findings[-1].code == "phase_warning"


def _analysis(
    *,
    lufs: float | None,
    peak_dbfs: float,
    phase_correlation: float | None = 1.0,
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
        phase_correlation=phase_correlation,
        spectral_centroid_hz=1_000.0,
    )
