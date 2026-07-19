"""Compatibility exports for analysis-engine input errors."""

from packages.audio_core.exceptions import (
    AudioInputError as AnalysisError,
)
from packages.audio_core.exceptions import (
    InvalidAudioFileError,
    UnsupportedAudioFormatError,
)

__all__ = ["AnalysisError", "InvalidAudioFileError", "UnsupportedAudioFormatError"]
