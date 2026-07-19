"""Retry-safe local task implementations used by dedicated Celery queues."""

from __future__ import annotations

from pathlib import Path

from packages.analysis_engine import AnalysisService
from packages.audio_core import decode_audio, encode_wav
from packages.dsp_engine import AutomaticMasteringService

from .celery_app import celery_app


@celery_app.task(
    name="openmaster.analysis", autoretry_for=(OSError,), retry_backoff=True, max_retries=3
)
def analyze_audio(input_path: str) -> dict[str, object]:
    """Analyse one immutable input path and return its JSON-safe measurements."""
    return AnalysisService().analyze(input_path).to_dict()


@celery_app.task(
    name="openmaster.mastering", autoretry_for=(OSError,), retry_backoff=True, max_retries=3
)
def master_audio(input_path: str, output_path: str) -> dict[str, object]:
    """Render deterministically to an idempotent explicit output destination."""
    decoded = decode_audio(input_path)
    analysis = AnalysisService().analyze_decoded(decoded)
    result = AutomaticMasteringService().master_to_wav(
        decoded.samples,
        decoded.metadata.sample_rate_hz,
        analysis,
        output_path,
        overwrite=True,
    )
    return {
        "output_path": str(result.output_path),
        "processors": result.mastering.render.applied_processors,
    }


@celery_app.task(
    name="openmaster.export", autoretry_for=(OSError,), retry_backoff=True, max_retries=3
)
def export_wav(input_path: str, output_path: str, bit_depth: int = 24) -> dict[str, object]:
    """Normalize a decoded source into a deterministic PCM WAV export destination."""
    decoded = decode_audio(input_path)
    output = encode_wav(
        Path(output_path),
        decoded.samples,
        decoded.metadata.sample_rate_hz,
        bit_depth=bit_depth,
        overwrite=True,
    )
    return {"output_path": str(output), "bit_depth": bit_depth}
