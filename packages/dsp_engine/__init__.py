"""Deterministic, composable DSP processors for OpenMaster mastering."""

from .automatic import (
    AutomaticMasteringResult,
    AutomaticMasteringService,
    MasteringDecision,
    MasteringPolicy,
)
from .gain import GainProcessor
from .limiter import LimiterProcessor
from .mastering import DeterministicMasteringService, MasteringResult, MasteringSettings
from .pipeline import DspPipeline
from .processor import DspProcessor

__all__ = [
    "AutomaticMasteringResult",
    "AutomaticMasteringService",
    "DeterministicMasteringService",
    "DspPipeline",
    "DspProcessor",
    "GainProcessor",
    "LimiterProcessor",
    "MasteringDecision",
    "MasteringPolicy",
    "MasteringResult",
    "MasteringSettings",
]
