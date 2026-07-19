"""Typed failures raised by reusable audio-input components."""


class AudioInputError(Exception):
    """Base exception for expected audio-input failures."""


class InvalidAudioFileError(AudioInputError):
    """Raised when an input file cannot be safely decoded."""


class UnsupportedAudioFormatError(AudioInputError):
    """Raised when an input format has no configured decoder."""
