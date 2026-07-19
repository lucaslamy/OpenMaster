"""Unit tests for reusable audio-core contracts."""

import wave
from pathlib import Path

import numpy as np
import pytest

from packages.audio_core import AudioMetadata, DecodedAudio, DecodeLimits, decode_wav


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


def test_decode_wav_returns_audio_core_contract(tmp_path: Path) -> None:
    path = tmp_path / "audio.wav"
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(48_000)
        output.writeframes(np.zeros(48_000, dtype="<i2").tobytes())

    decoded = decode_wav(path)

    assert decoded.samples.shape == (48_000, 1)
    assert decoded.metadata.duration_seconds == 1.0
