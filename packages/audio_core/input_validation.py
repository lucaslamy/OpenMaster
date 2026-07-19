"""Safety checks and resource limits for local audio inputs."""

from pathlib import Path

from .exceptions import InvalidAudioFileError

MAX_SAMPLE_VALUES = 120_000_000


def validate_audio_path(path: str | Path) -> Path:
    """Validate that an audio input resolves to a regular local file."""
    audio_path = Path(path)
    if not audio_path.is_file():
        raise InvalidAudioFileError(f"Audio file does not exist: {audio_path}")
    return audio_path
