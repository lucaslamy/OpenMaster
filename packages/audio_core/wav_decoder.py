"""Safe PCM and IEEE-float WAV decoding for OpenMaster audio consumers."""

import wave
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from .exceptions import InvalidAudioFileError, UnsupportedAudioFormatError
from .input_validation import validate_audio_path
from .limits import DEFAULT_DECODE_LIMITS, DecodeLimits
from .models import AudioMetadata, DecodedAudio, FloatSamples

WAV_SUFFIXES = frozenset({".wav", ".wave"})


def decode_wav(path: str | Path, *, limits: DecodeLimits = DEFAULT_DECODE_LIMITS) -> DecodedAudio:
    """Decode a WAV file into normalized samples and validated metadata."""
    audio_path = validate_audio_path(path)
    if audio_path.suffix.lower() not in WAV_SUFFIXES:
        raise UnsupportedAudioFormatError("Only WAV input is supported by this decoder")
    try:
        with wave.open(str(audio_path), "rb") as source:
            channels = source.getnchannels()
            sample_width = source.getsampwidth()
            sample_rate = source.getframerate()
            frames = source.getnframes()
            if source.getcomptype() != "NONE":
                raise UnsupportedAudioFormatError("Compressed WAV input is not supported")
            if channels < 1 or sample_rate < 1 or frames < 1:
                raise InvalidAudioFileError("WAV header has invalid audio dimensions")
            if frames * channels > limits.max_sample_values:
                raise InvalidAudioFileError("Audio file exceeds the analysis sample limit")
            raw = source.readframes(frames)
    except wave.Error as error:
        return _decode_float_wav(audio_path, limits, error)
    samples = _decode_pcm(raw, sample_width)
    if samples.size != frames * channels:
        raise InvalidAudioFileError("WAV data length does not match its header")
    return DecodedAudio(
        samples.reshape(frames, channels),
        AudioMetadata(sample_rate, channels, frames, sample_width * 8, "wav"),
    )


def _decode_float_wav(path: Path, limits: DecodeLimits, original_error: wave.Error) -> DecodedAudio:
    """Decode IEEE-float WAV data rejected by :mod:`wave`."""
    try:
        sample_rate, source_samples = wavfile.read(path)
    except (OSError, ValueError):
        raise InvalidAudioFileError(f"Invalid WAV file: {path}") from original_error
    samples = np.asarray(source_samples)
    if samples.ndim == 1:
        samples = samples[:, np.newaxis]
    if samples.ndim != 2 or samples.shape[0] < 1 or samples.shape[1] < 1 or sample_rate < 1:
        raise InvalidAudioFileError("WAV file has invalid audio dimensions")
    if samples.size > limits.max_sample_values:
        raise InvalidAudioFileError("Audio file exceeds the analysis sample limit")
    if samples.dtype.kind != "f" or samples.dtype.itemsize not in {4, 8}:
        raise InvalidAudioFileError(f"Invalid WAV file: {path}")
    normalized = samples.astype(np.float64, copy=False)
    if not np.isfinite(normalized).all():
        raise InvalidAudioFileError("WAV file contains non-finite samples")
    return DecodedAudio(
        normalized,
        AudioMetadata(
            int(sample_rate), samples.shape[1], samples.shape[0], samples.dtype.itemsize * 8, "wav"
        ),
    )


def _decode_pcm(raw: bytes, sample_width: int) -> FloatSamples:
    """Convert 8/16/24/32-bit little-endian PCM bytes into float64 samples."""
    if sample_width == 1:
        return (np.frombuffer(raw, dtype=np.uint8).astype(np.float64) - 128.0) / 128.0
    if sample_width == 2:
        return np.frombuffer(raw, dtype="<i2").astype(np.float64) / 32768.0
    if sample_width == 3:
        values = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        signed = values[:, 0] | (values[:, 1] << 8) | (values[:, 2] << 16)
        signed = np.where(signed & 0x800000, signed - 0x1000000, signed)
        return signed.astype(np.float64) / 8388608.0
    if sample_width == 4:
        return np.frombuffer(raw, dtype="<i4").astype(np.float64) / 2147483648.0
    raise UnsupportedAudioFormatError(f"Unsupported PCM bit depth: {sample_width * 8}")
