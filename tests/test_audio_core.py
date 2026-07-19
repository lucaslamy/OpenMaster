"""Unit tests for reusable audio-core contracts."""

import numpy as np
import pytest

from packages.audio_core import AudioMetadata, DecodedAudio, DecodeLimits


def test_audio_metadata_derives_duration() -> None:
    metadata = AudioMetadata(
        sample_rate_hz=48_000,
        channels=2,
        frame_count=96_000,
        bit_depth=24,
        source_format="wav",
    )

    assert metadata.duration_seconds == 2.0


@pytest.mark.parametrize("max_sample_values, timeout", [(0, 1), (1, 0)])
def test_decode_limits_require_positive_values(max_sample_values: int, timeout: int) -> None:
    with pytest.raises(ValueError, match="must be positive"):
        DecodeLimits(max_sample_values=max_sample_values, process_timeout_seconds=timeout)


def test_decoded_audio_rejects_shape_mismatch() -> None:
    metadata = AudioMetadata(48_000, 2, 10, 16, "wav")
    with pytest.raises(ValueError, match="does not match"):
        DecodedAudio(np.zeros((10, 1), dtype=np.float64), metadata)
