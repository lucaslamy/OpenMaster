"""Tests for deterministic DSP processor contracts."""

import numpy as np
import pytest

from packages.dsp_engine import DspPipeline, GainProcessor


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
