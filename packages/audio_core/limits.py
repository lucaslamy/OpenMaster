"""Resource limits applied before audio samples enter DSP analysis."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DecodeLimits:
    """Bound sample allocation and external decoder execution time."""

    max_sample_values: int = 120_000_000
    process_timeout_seconds: int = 120

    def __post_init__(self) -> None:
        """Reject invalid limits at construction time."""
        if self.max_sample_values < 1 or self.process_timeout_seconds < 1:
            raise ValueError("Decode limits must be positive")


DEFAULT_DECODE_LIMITS = DecodeLimits()
