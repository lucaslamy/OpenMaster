"""Reusable audio input contracts shared by OpenMaster audio packages."""

from .exceptions import AudioInputError, InvalidAudioFileError, UnsupportedAudioFormatError
from .input_validation import MAX_SAMPLE_VALUES, validate_audio_path
from .limits import DEFAULT_DECODE_LIMITS, DecodeLimits
from .models import AudioMetadata, DecodedAudio, FloatSamples

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
    "validate_audio_path",
]
