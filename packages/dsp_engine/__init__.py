"""Deterministic, composable DSP processors for OpenMaster mastering."""

from .automatic import (
    AutomaticMasteringResult,
    AutomaticMasteringService,
    ExportedMasteringResult,
    MasteringDecision,
    MasteringPolicy,
)
from .clipper import OversampledClipperProcessor
from .equalizer import TonalEqualizerProcessor
from .gain import GainProcessor
from .limiter import LimiterProcessor
from .mastering import DeterministicMasteringService, MasteringResult, MasteringSettings
from .pipeline import DspPipeline
from .processor import DspProcessor
from .saturation import SaturationProcessor
from .spectral_dynamics import (
    BassControlProcessor,
    DeEsserProcessor,
    DynamicEqualizerProcessor,
    HighPassProcessor,
)

__all__ = [
    "AutomaticMasteringResult",
    "AutomaticMasteringService",
    "BassControlProcessor",
    "DeEsserProcessor",
    "DeterministicMasteringService",
    "DspPipeline",
    "DspProcessor",
    "DynamicEqualizerProcessor",
    "ExportedMasteringResult",
    "GainProcessor",
    "HighPassProcessor",
    "LimiterProcessor",
    "MasteringDecision",
    "MasteringPolicy",
    "OversampledClipperProcessor",
    "SaturationProcessor",
    "TonalEqualizerProcessor",
    "MasteringResult",
    "MasteringSettings",
]
