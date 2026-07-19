"""Composable deterministic processor pipeline."""

from dataclasses import dataclass

from packages.audio_core import FloatSamples

from .processor import DspProcessor


@dataclass(frozen=True, slots=True)
class DspPipeline:
    """Apply an ordered sequence of processors with an explicit sample rate."""

    processors: tuple[DspProcessor, ...]

    def process(self, samples: FloatSamples, sample_rate_hz: int) -> FloatSamples:
        """Apply processors in order, returning a new deterministic output buffer."""
        output = samples
        for processor in self.processors:
            output = processor.process(output, sample_rate_hz)
        return output
