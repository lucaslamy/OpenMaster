"""Tests for deterministic DSP processor contracts."""

import numpy as np
import pytest

from packages.dsp_engine import (
    DeterministicMasteringService,
    DspPipeline,
    GainProcessor,
    LimiterProcessor,
    MasteringSettings,
)


def test_gain_processor_scales_without_mutating_input() -> None:
    samples = np.full((8, 2), 0.25, dtype=np.float64)

    output = GainProcessor(6.0206).process(samples, 48_000)

    assert output == pytest.approx(np.full((8, 2), 0.5))
    assert samples == pytest.approx(np.full((8, 2), 0.25))


def test_pipeline_applies_processors_in_order() -> None:
    samples = np.ones((4, 1), dtype=np.float64)

    output = DspPipeline((GainProcessor(6.0206), GainProcessor(-6.0206))).process(samples, 48_000)

    assert output == pytest.approx(samples)


def test_gain_processor_rejects_invalid_audio() -> None:
    with pytest.raises(ValueError, match="shape"):
        GainProcessor(0.0).process(np.array([1.0]), 48_000)


def test_limiter_enforces_linked_stereo_ceiling() -> None:
    samples = np.array([[2.0, 1.0], [0.2, -0.1]], dtype=np.float64)

    output = LimiterProcessor(-6.0206).process(samples, 48_000)

    assert np.max(np.abs(output)) == pytest.approx(0.5, abs=1e-5)
    assert output[0, 1] / output[0, 0] == pytest.approx(0.5)
    assert output[1] == pytest.approx(samples[1])


def test_limiter_rejects_ceiling_above_full_scale() -> None:
    with pytest.raises(ValueError, match="at or below"):
        LimiterProcessor(0.1)


def test_mastering_service_reports_deterministic_processor_order() -> None:
    samples = np.array([[1.0], [0.25]], dtype=np.float64)

    result = DeterministicMasteringService().master(
        samples,
        48_000,
        MasteringSettings(input_gain_db=6.0206, ceiling_dbfs=-1.0),
    )

    assert result.applied_processors == ("gain", "sample_peak_limiter")
    assert np.max(np.abs(result.samples)) == pytest.approx(10 ** (-1.0 / 20.0))
    assert samples == pytest.approx(np.array([[1.0], [0.25]], dtype=np.float64))
