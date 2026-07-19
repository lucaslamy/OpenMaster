"""Tests for deterministic balance-preserving stem-group mastering."""

import numpy as np
import pytest

from packages.analysis_engine import AnalysisResult
from packages.audio_core import AudioMetadata, DecodedAudio
from packages.dsp_engine import MasteringPolicy
from packages.stem_mastering import StemGroupMasteringService


def test_stem_group_mastering_limits_the_sum_with_one_shared_envelope() -> None:
    stems = {
        "drums": _decoded(np.array([[0.8, 0.4], [0.1, 0.2]], dtype=np.float64)),
        "music": _decoded(np.array([[0.8, 0.4], [0.1, 0.2]], dtype=np.float64)),
    }
    policy = MasteringPolicy(target_lufs=-14.0, ceiling_dbfs=-1.0)

    result = StemGroupMasteringService().master(stems, _analysis(), policy)
    rendered = {stem.name: stem.samples for stem in result.stems}
    rendered_sum = rendered["drums"] + rendered["music"]

    assert result.applied_processors == ("shared_gain", "group_sample_peak_limiter")
    assert np.max(np.abs(rendered_sum)) == pytest.approx(10 ** (-1.0 / 20.0))
    assert rendered["drums"] == pytest.approx(rendered["music"])
    assert result.decision_policy == policy


def test_stem_group_mastering_rejects_misaligned_stems() -> None:
    stems = {
        "drums": _decoded(np.zeros((2, 2), dtype=np.float64)),
        "music": _decoded(np.zeros((3, 2), dtype=np.float64)),
    }

    with pytest.raises(ValueError, match="same frame and channel shape"):
        StemGroupMasteringService().master(stems, _analysis())


def _decoded(samples: np.ndarray) -> DecodedAudio:
    return DecodedAudio(
        samples,
        AudioMetadata(
            sample_rate_hz=48_000,
            channels=samples.shape[1],
            frame_count=samples.shape[0],
            bit_depth=24,
            source_format="wav",
        ),
    )


def _analysis() -> AnalysisResult:
    return AnalysisResult(
        duration_seconds=1.0,
        sample_rate_hz=48_000,
        bit_depth=24,
        channels=2,
        lufs=-14.0,
        rms_dbfs=-18.0,
        peak_dbfs=-20.0,
        true_peak_dbfs=-20.0,
        dynamic_range_db=9.0,
        crest_factor_db=6.0,
        bpm=None,
        musical_key=None,
        stereo_width=0.5,
        phase_correlation=1.0,
        spectral_centroid_hz=1_000.0,
    )
