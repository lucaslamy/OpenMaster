"""Domain exceptions raised by the audio analysis engine."""


class AnalysisError(Exception):
    """Base exception for expected analysis failures."""


class InvalidAudioFileError(AnalysisError):
    """Raised when an input file cannot be safely analysed."""


class UnsupportedAudioFormatError(AnalysisError):
    """Raised when the input format has no configured decoder."""
