"""Format dispatcher for validated OpenMaster audio input."""

from pathlib import Path

from .exceptions import UnsupportedAudioFormatError
from .ffmpeg_decoder import FFMPEG_SUFFIXES, decode_with_ffmpeg
from .input_validation import validate_audio_path
from .limits import DEFAULT_DECODE_LIMITS, DecodeLimits
from .models import DecodedAudio
from .wav_decoder import WAV_SUFFIXES, decode_wav

SUPPORTED_AUDIO_SUFFIXES = WAV_SUFFIXES | FFMPEG_SUFFIXES


def decode_audio(path: str | Path, *, limits: DecodeLimits = DEFAULT_DECODE_LIMITS) -> DecodedAudio:
    """Decode any supported local audio file through the appropriate adapter."""
    audio_path = validate_audio_path(path)
    suffix = audio_path.suffix.lower()
    if suffix in WAV_SUFFIXES:
        return decode_wav(audio_path, limits=limits)
    if suffix in FFMPEG_SUFFIXES:
        return decode_with_ffmpeg(audio_path, limits=limits)
    supported = ", ".join(sorted(SUPPORTED_AUDIO_SUFFIXES))
    raise UnsupportedAudioFormatError(f"Unsupported audio format; supported: {supported}")
