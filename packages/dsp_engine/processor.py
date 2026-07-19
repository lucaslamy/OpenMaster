"""Common typed contract implemented by deterministic DSP processors."""

from typing import Protocol

from packages.audio_core import FloatSamples


class DspProcessor(Protocol):
    """Transform normalized audio samples without hidden state or side effects."""

    def process(self, samples: FloatSamples, sample_rate_hz: int) -> FloatSamples:
        """Return processed audio with the same frame and channel dimensions."""
