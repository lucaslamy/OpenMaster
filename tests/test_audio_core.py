"""Unit tests for reusable audio-core contracts."""

import wave
from pathlib import Path

import numpy as np
import pytest

from packages.audio_core import (
    AudioMetadata,
    DecodedAudio,
    DecodeLimits,
    InvalidAudioFileError,
    UnsupportedAudioFormatError,
    decode_audio,
    decode_wav,
    encode_wav,
    waveform_envelope,
)


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


def test_decode_audio_validates_path_before_format(tmp_path: Path) -> None:
    with pytest.raises(InvalidAudioFileError):
        decode_audio(tmp_path / "missing.unknown")
    unsupported = tmp_path / "audio.unknown"
    unsupported.write_bytes(b"not audio")
    with pytest.raises(UnsupportedAudioFormatError):
        decode_audio(unsupported)


def test_encode_wav_round_trips_24_bit_stereo_audio(tmp_path: Path) -> None:
    path = tmp_path / "master.wav"
    samples = np.array([[-1.0, 1.0], [-0.25, 0.25]], dtype=np.float64)

    output = encode_wav(path, samples, 48_000)
    decoded = decode_wav(output)

    assert output == path
    assert decoded.metadata.sample_rate_hz == 48_000
    assert decoded.metadata.bit_depth == 24
    assert decoded.samples == pytest.approx(samples, abs=1.5e-7)


def test_encode_wav_refuses_unrequested_overwrite_and_invalid_samples(tmp_path: Path) -> None:
    path = tmp_path / "master.wav"
    path.write_bytes(b"existing")

    with pytest.raises(FileExistsError, match="already exists"):
        encode_wav(path, np.zeros((1, 1), dtype=np.float64), 48_000)
    with pytest.raises(ValueError, match="normalized"):
        encode_wav(
            tmp_path / "invalid.wav",
            np.array([[1.01]], dtype=np.float64),
            48_000,
        )


def test_waveform_envelope_is_compact_normalized_and_channel_aware() -> None:
    samples = np.array(
        [[0.0, 0.25], [0.5, -1.0], [0.1, 0.2], [-0.5, 0.0]],
        dtype=np.float64,
    )

    envelope = waveform_envelope(samples, points=16)

    assert len(envelope) == 16
    assert max(envelope) == 1.0
    assert min(envelope) >= 0.0


def test_waveform_envelope_handles_silence_and_rejects_unsafe_size() -> None:
    assert waveform_envelope(np.zeros((10, 2), dtype=np.float64), points=16) == [0.0] * 16
    quiet = waveform_envelope(np.full((32, 1), 0.25, dtype=np.float64), points=16)
    assert quiet == [0.25] * 16
    with pytest.raises(ValueError, match="between 16 and 2048"):
        waveform_envelope(np.zeros((10, 1), dtype=np.float64), points=8)
