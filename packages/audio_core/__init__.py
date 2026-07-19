"""Reusable audio input contracts shared by OpenMaster audio packages."""

from .exceptions import AudioInputError, InvalidAudioFileError, UnsupportedAudioFormatError
from .input_validation import MAX_SAMPLE_VALUES, validate_audio_path
from .limits import DEFAULT_DECODE_LIMITS, DecodeLimits
from .models import AudioMetadata, DecodedAudio, FloatSamples
from .wav_decoder import WAV_SUFFIXES, decode_wav

__all__ = [
    "AudioInputError",
    "AudioMetadata",
    "DecodedAudio",
    "DecodeLimits",
    "DEFAULT_DECODE_LIMITS",
    "FloatSamples",
    "InvalidAudioFileError",
    "MAX_SAMPLE_VALUES",
    "UnsupportedAudioFormatError",
    "WAV_SUFFIXES",
    "decode_wav",
    "validate_audio_path",
]
