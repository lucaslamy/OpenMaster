"""Reusable audio input contracts shared by OpenMaster audio packages."""

from .decoder import SUPPORTED_AUDIO_SUFFIXES, decode_audio
from .exceptions import AudioInputError, InvalidAudioFileError, UnsupportedAudioFormatError
from .ffmpeg_decoder import FFMPEG_SUFFIXES, decode_with_ffmpeg
from .input_validation import MAX_SAMPLE_VALUES, validate_audio_path
from .limits import DEFAULT_DECODE_LIMITS, DecodeLimits
from .models import AudioMetadata, DecodedAudio, FloatSamples
from .wav_decoder import WAV_SUFFIXES, decode_wav
from .wav_encoder import encode_wav
from .waveform import waveform_envelope

__all__ = [
    "AudioInputError",
    "AudioMetadata",
    "DecodedAudio",
    "DecodeLimits",
    "DEFAULT_DECODE_LIMITS",
    "FloatSamples",
    "FFMPEG_SUFFIXES",
    "InvalidAudioFileError",
    "MAX_SAMPLE_VALUES",
    "UnsupportedAudioFormatError",
    "SUPPORTED_AUDIO_SUFFIXES",
    "WAV_SUFFIXES",
    "decode_wav",
    "encode_wav",
    "waveform_envelope",
    "decode_audio",
    "decode_with_ffmpeg",
    "validate_audio_path",
]
