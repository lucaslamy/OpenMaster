"""Apply one auditable mastering decision to a time-aligned group of stems."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np

from packages.analysis_engine import AnalysisResult
from packages.audio_core import DecodedAudio, FloatSamples
from packages.compute_backends import ComputeBackend, NumpyComputeBackend
from packages.dsp_engine import AutomaticMasteringService, MasteringDecision, MasteringPolicy


@dataclass(frozen=True, slots=True)
class MasteredStem:
    """One rendered stem, identified by its stable caller-provided name."""

    name: str
    samples: FloatSamples


@dataclass(frozen=True, slots=True)
class StemMasteringResult:
    """Rendered aligned stems and the one decision shared by the whole group."""

    stems: tuple[MasteredStem, ...]
    sample_rate_hz: int
    decision: MasteringDecision
    decision_policy: MasteringPolicy
    applied_processors: tuple[str, ...]


class StemGroupMasteringService:
    """Master aligned stems while preserving their sample-by-sample group balance."""

    def __init__(self, backend: ComputeBackend | None = None) -> None:
        """Use the explicit CPU reference backend unless another backend is selected."""
        self._backend = backend or NumpyComputeBackend()

    def master(
        self,
        stems: Mapping[str, DecodedAudio],
        mix_analysis: AnalysisResult,
        policy: MasteringPolicy | None = None,
    ) -> StemMasteringResult:
        """Apply shared static gain and a shared linked sample-peak limiter envelope."""
        ordered_stems, sample_rate_hz = _validate_and_order_stems(stems)
        effective_policy = policy or MasteringPolicy()
        decision = AutomaticMasteringService(effective_policy).decide(mix_analysis)
        gain = 10.0 ** (decision.settings.input_gain_db / 20.0)
        ceiling = 10.0 ** (decision.settings.ceiling_dbfs / 20.0)
        names = tuple(name for name, _ in ordered_stems)
        rendered_samples = self._backend.render_group(
            tuple(audio.samples for _, audio in ordered_stems),
            gain=gain,
            ceiling=ceiling,
        )
        rendered_stems = tuple(
            MasteredStem(name, samples)
            for name, samples in zip(names, rendered_samples, strict=True)
        )
        return StemMasteringResult(
            stems=rendered_stems,
            sample_rate_hz=sample_rate_hz,
            decision=decision,
            decision_policy=effective_policy,
            applied_processors=("shared_gain", "group_sample_peak_limiter"),
        )


def _validate_and_order_stems(
    stems: Mapping[str, DecodedAudio],
) -> tuple[tuple[tuple[str, DecodedAudio], ...], int]:
    """Ensure stems can be summed frame-by-frame before rendering them as a group."""
    if not stems:
        raise ValueError("At least one stem is required")
    ordered_stems = tuple(sorted(stems.items()))
    first_name, first_audio = ordered_stems[0]
    if not first_name:
        raise ValueError("Stem names must not be empty")
    expected_shape = first_audio.samples.shape
    sample_rate_hz = first_audio.metadata.sample_rate_hz
    for name, audio in ordered_stems:
        if not name:
            raise ValueError("Stem names must not be empty")
        if audio.metadata.sample_rate_hz != sample_rate_hz:
            raise ValueError("All stems must share the same sample rate")
        if audio.samples.shape != expected_shape:
            raise ValueError("All stems must share the same frame and channel shape")
        if not np.isfinite(audio.samples).all():
            raise ValueError("Stem samples must be finite")
    return ordered_stems, sample_rate_hz
