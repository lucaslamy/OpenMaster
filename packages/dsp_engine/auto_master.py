"""Named composition root for deterministic automatic-mastering processors."""

from dataclasses import dataclass

from packages.audio_core import FloatSamples

from .pipeline import DspPipeline
from .processor import DspProcessor


@dataclass(frozen=True, slots=True)
class AutoMasterPipeline:
    """Run explicitly configured deterministic mastering processors in sequence."""

    processors: tuple[DspProcessor, ...]

    def process(self, samples: FloatSamples, sample_rate_hz: int) -> FloatSamples:
        """Process audio through the configured mastering chain."""
        return DspPipeline(self.processors).process(samples, sample_rate_hz)
