"""Safe PCM WAV decoding used by the CPU-only analysis engine."""

import wave
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from scipy.io import wavfile

from .exceptions import InvalidAudioFileError, UnsupportedAudioFormatError

FloatSamples = NDArray[np.float64]
MAX_SAMPLE_VALUES = 120_000_000


def read_wav(path: str | Path) -> tuple[FloatSamples, int, int]:
    """Decode an integer PCM WAV file into normalized samples and metadata.

    The returned matrix has shape ``(frames, channels)`` and values in [-1, 1].
    A bounded input prevents a malformed file from forcing unbounded allocation.
    """
    audio_path = validate_audio_path(path)
    if audio_path.suffix.lower() not in {".wav", ".wave"}:
        raise UnsupportedAudioFormatError("Only PCM WAV input is supported by this decoder")

    try:
        with wave.open(str(audio_path), "rb") as source:
            channels = source.getnchannels()
            sample_width = source.getsampwidth()
            sample_rate = source.getframerate()
            frames = source.getnframes()
            compression = source.getcomptype()
            if compression != "NONE":
                raise UnsupportedAudioFormatError("Compressed WAV input is not supported")
            if channels < 1 or sample_rate < 1 or frames < 1:
                raise InvalidAudioFileError("WAV header has invalid audio dimensions")
            if frames * channels > MAX_SAMPLE_VALUES:
                raise InvalidAudioFileError("Audio file exceeds the analysis sample limit")
            raw = source.readframes(frames)
    except wave.Error as error:
        return _read_wav_with_scipy(audio_path, error)

    samples = _decode_pcm(raw, sample_width)
    expected_values = frames * channels
    if samples.size != expected_values:
        raise InvalidAudioFileError("WAV data length does not match its header")
    return samples.reshape(frames, channels), sample_rate, sample_width * 8


def _read_wav_with_scipy(path: Path, original_error: wave.Error) -> tuple[FloatSamples, int, int]:
    """Read IEEE-float WAV data that the standard :mod:`wave` module rejects."""
    try:
        sample_rate, source_samples = wavfile.read(path)
    except (OSError, ValueError):
        raise InvalidAudioFileError(f"Invalid WAV file: {path}") from original_error
    samples = np.asarray(source_samples)
    if samples.ndim == 1:
        samples = samples[:, np.newaxis]
    if samples.ndim != 2 or samples.shape[0] < 1 or samples.shape[1] < 1 or sample_rate < 1:
        raise InvalidAudioFileError("WAV file has invalid audio dimensions")
    if samples.size > MAX_SAMPLE_VALUES:
        raise InvalidAudioFileError("Audio file exceeds the analysis sample limit")
    if samples.dtype.kind != "f" or samples.dtype.itemsize not in {4, 8}:
        raise InvalidAudioFileError(f"Invalid WAV file: {path}")
    normalized = samples.astype(np.float64, copy=False)
    if not np.isfinite(normalized).all():
        raise InvalidAudioFileError("WAV file contains non-finite samples")
    return normalized, int(sample_rate), samples.dtype.itemsize * 8


def validate_audio_path(path: str | Path) -> Path:
    """Validate that an input points to a regular local file."""
    audio_path = Path(path)
    if not audio_path.is_file():
        raise InvalidAudioFileError(f"Audio file does not exist: {audio_path}")
    return audio_path


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
