"""Retry-safe local task implementations used by dedicated Celery queues."""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import cast

from packages.ai_mastering import LamAiMasteringClient, LamAiMasteringError
from packages.analysis_engine import AnalysisResult, AnalysisService
from packages.audio_core import (
    decode_audio,
    encode_wav,
    level_timeline,
    spectral_profile,
    waveform_envelope,
)
from packages.database import AnalysisJobRecord, AnalysisJobRepository
from packages.dsp_engine import AutomaticMasteringService, MasteringPolicy
from packages.mastering_assistant import MasteringAssistant
from packages.remote_compute import RemoteMasteringRequest, RunPodClient
from packages.storage import MinioObjectStore, MinioSignedUrlService

from .celery_app import celery_app


@celery_app.task(
    name="openmaster.analysis", autoretry_for=(OSError,), retry_backoff=True, max_retries=3
)
def analyze_audio(input_path: str) -> dict[str, object]:
    """Analyse one immutable input path and return its JSON-safe measurements."""
    return AnalysisService().analyze(input_path).to_dict()


@celery_app.task(name="openmaster.analysis_object")
def analyze_minio_object(job_id: str, object_name: str) -> dict[str, object]:
    """Download an immutable MinIO object and persist its analysis result."""
    repository = AnalysisJobRepository.from_environment()
    repository.mark_running(job_id)
    try:
        suffix = Path(object_name).suffix.lower()
        with tempfile.TemporaryDirectory(prefix="openmaster-analysis-") as directory:
            source = Path(directory) / f"source{suffix}"
            MinioObjectStore.from_environment().download(object_name, source)
            result = AnalysisService().analyze(source).to_dict()
        repository.mark_analysis_complete(job_id, result)
        master_minio_object.apply_async(args=(job_id, object_name), queue="mastering")
        return result
    except Exception as error:
        repository.mark_failed(
            job_id,
            type(error).__name__,
            "Audio analysis failed; inspect the analysis worker logs",
        )
        raise


@celery_app.task(name="openmaster.mastering_object")
def master_minio_object(job_id: str, object_name: str) -> dict[str, object]:
    """Render, upload, and persist an auditable WAV master for one analysed job."""
    repository = AnalysisJobRepository.from_environment()
    job = repository.get(job_id)
    if job is None or job.result is None:
        raise ValueError("Analysis result is required before mastering")
    output_object = f"mastering/{job_id}/{_master_filename(job)}"
    storage = MinioObjectStore.from_environment()
    try:
        with tempfile.TemporaryDirectory(prefix="openmaster-mastering-") as directory:
            suffix = Path(object_name).suffix.lower()
            source = Path(directory) / f"source{suffix}"
            destination = Path(directory) / "master.wav"
            storage.download(object_name, source)
            analysis = AnalysisResult(**job.result)
            effective_policy = _job_policy(job)
            ai_assistance: dict[str, object] = {
                "requested": job.ai_assist_enabled,
                "applied": False,
            }
            if job.ai_assist_enabled:
                if os.environ.get("LAMAI_ENABLED", "false").lower() == "true":
                    try:
                        advice = LamAiMasteringClient.from_environment().recommend(
                            analysis,
                            effective_policy,
                        )
                        effective_policy = advice.policy
                        ai_assistance = {
                            "requested": True,
                            "applied": True,
                            "model": advice.model,
                            "rationale": advice.rationale,
                        }
                    except (LamAiMasteringError, OSError, ValueError):
                        ai_assistance["fallback_reason"] = "lamai_advice_unavailable"
                else:
                    ai_assistance["fallback_reason"] = "lamai_not_configured"
            recommendation = MasteringAssistant().recommend(
                analysis,
                target_lufs=effective_policy.target_lufs,
                maximum_gain_adjustment_db=effective_policy.maximum_gain_adjustment_db,
                ceiling_dbfs=effective_policy.ceiling_dbfs,
            )
            if os.environ.get("OPENMASTER_REMOTE_COMPUTE_ENABLED", "false").lower() == "true":
                source_sha256 = _sha256_file(source)
                remote_result = cast(
                    dict[str, object],
                    remote_master_minio_object.run(
                        object_name,
                        output_object,
                        source_sha256,
                        effective_policy.target_lufs,
                        effective_policy.maximum_gain_adjustment_db,
                        effective_policy.ceiling_dbfs,
                        job.bit_depth,
                        effective_policy.eq_low_gain_db,
                        effective_policy.eq_mid_gain_db,
                        effective_policy.eq_high_gain_db,
                        effective_policy.clipper_drive_db,
                        effective_policy.limiter_lookahead_ms,
                        effective_policy.limiter_release_ms,
                        effective_policy.high_pass_enabled,
                        effective_policy.high_pass_cutoff_hz,
                        effective_policy.dynamic_eq_reduction_db,
                        effective_policy.bass_control_reduction_db,
                        effective_policy.de_esser_reduction_db,
                        effective_policy.saturation_amount,
                    ),
                )
                mastering_result: dict[str, object] = {
                    "execution": "runpod",
                    **remote_result,
                    "bit_depth": job.bit_depth,
                    "ai_assistance": ai_assistance,
                }
                output = remote_result.get("output")
                if not isinstance(output, dict):
                    raise ValueError("RunPod result does not contain waveform output")
                source_waveform = _waveform_list(output.get("source_waveform"))
                master_waveform = _waveform_list(output.get("master_waveform"))
                source_spectrum = _visualization_list(output.get("source_spectrum"))
                master_spectrum = _visualization_list(output.get("master_spectrum"))
                source_level_timeline = _visualization_list(output.get("source_level_timeline"))
                master_level_timeline = _visualization_list(output.get("master_level_timeline"))
            else:
                decoded = decode_audio(source)
                mastered = AutomaticMasteringService(effective_policy).master_to_wav(
                    decoded.samples,
                    decoded.metadata.sample_rate_hz,
                    analysis,
                    destination,
                    bit_depth=job.bit_depth,
                )
                with mastered.output_path.open("rb") as stream:
                    storage.upload(
                        output_object,
                        stream,
                        length=mastered.output_path.stat().st_size,
                        content_type="audio/wav",
                    )
                mastering_result = {
                    "execution": "local",
                    "decision": asdict(mastered.mastering.decision),
                    "processors": list(mastered.mastering.render.applied_processors),
                    "bit_depth": job.bit_depth,
                    "output_lufs": mastered.mastering.render.output_lufs,
                    "output_true_peak_dbfs": mastered.mastering.render.output_true_peak_dbfs,
                    "dither_applied": mastered.dither_applied,
                    "ai_assistance": ai_assistance,
                }
                source_waveform = waveform_envelope(decoded.samples)
                master_waveform = waveform_envelope(mastered.mastering.render.samples)
                source_spectrum = spectral_profile(decoded.samples, decoded.metadata.sample_rate_hz)
                master_spectrum = spectral_profile(
                    mastered.mastering.render.samples,
                    decoded.metadata.sample_rate_hz,
                )
                source_level_timeline = level_timeline(decoded.samples)
                master_level_timeline = level_timeline(mastered.mastering.render.samples)
        repository.mark_mastered(
            job_id,
            recommendation={
                **recommendation.to_dict(),
                "ai_assistance": ai_assistance,
            },
            mastering_result=mastering_result,
            output_object_name=output_object,
            source_waveform=source_waveform,
            master_waveform=master_waveform,
            source_spectrum=source_spectrum,
            master_spectrum=master_spectrum,
            source_level_timeline=source_level_timeline,
            master_level_timeline=master_level_timeline,
        )
        return mastering_result
    except Exception as error:
        repository.mark_failed(
            job_id,
            type(error).__name__,
            "Mastering failed; inspect the mastering worker logs",
        )
        raise


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


@celery_app.task(name="openmaster.remote_mastering")
def remote_master_audio(
    source_url: str,
    destination_url: str,
    source_sha256: str,
    target_lufs: float = -14.0,
    maximum_gain_adjustment_db: float = 12.0,
    ceiling_dbfs: float = -1.0,
    bit_depth: int = 24,
    eq_low_gain_db: float = 0.0,
    eq_mid_gain_db: float = 0.0,
    eq_high_gain_db: float = 0.0,
    clipper_drive_db: float = 0.0,
    limiter_lookahead_ms: float = 3.0,
    limiter_release_ms: float = 80.0,
    high_pass_enabled: bool = True,
    high_pass_cutoff_hz: float = 25.0,
    dynamic_eq_reduction_db: float = 0.0,
    bass_control_reduction_db: float = 0.0,
    de_esser_reduction_db: float = 0.0,
    saturation_amount: float = 0.0,
) -> dict[str, object]:
    """Delegate one heavy job to RunPod while the local worker only monitors it."""
    endpoint_id = os.environ.get("RUNPOD_ENDPOINT_ID", "")
    api_key = os.environ.get("RUNPOD_API_KEY", "")
    client = RunPodClient(endpoint_id, api_key)
    submitted = client.submit_mastering(
        RemoteMasteringRequest(
            source_url=source_url,
            destination_url=destination_url,
            source_sha256=source_sha256,
            target_lufs=target_lufs,
            maximum_gain_adjustment_db=maximum_gain_adjustment_db,
            ceiling_dbfs=ceiling_dbfs,
            eq_low_gain_db=eq_low_gain_db,
            eq_mid_gain_db=eq_mid_gain_db,
            eq_high_gain_db=eq_high_gain_db,
            clipper_drive_db=clipper_drive_db,
            limiter_lookahead_ms=limiter_lookahead_ms,
            limiter_release_ms=limiter_release_ms,
            high_pass_enabled=high_pass_enabled,
            high_pass_cutoff_hz=high_pass_cutoff_hz,
            dynamic_eq_reduction_db=dynamic_eq_reduction_db,
            bass_control_reduction_db=bass_control_reduction_db,
            de_esser_reduction_db=de_esser_reduction_db,
            saturation_amount=saturation_amount,
            bit_depth=bit_depth,
        )
    )
    completed = client.wait(submitted.id)
    return {
        "remote_job_id": completed.id,
        "remote_status": completed.status.value,
        "output": completed.output or {},
    }


@celery_app.task(name="openmaster.remote_mastering_minio")
def remote_master_minio_object(
    source_object: str,
    destination_object: str,
    source_sha256: str,
    target_lufs: float = -14.0,
    maximum_gain_adjustment_db: float = 12.0,
    ceiling_dbfs: float = -1.0,
    bit_depth: int = 24,
    eq_low_gain_db: float = 0.0,
    eq_mid_gain_db: float = 0.0,
    eq_high_gain_db: float = 0.0,
    clipper_drive_db: float = 0.0,
    limiter_lookahead_ms: float = 3.0,
    limiter_release_ms: float = 80.0,
    high_pass_enabled: bool = True,
    high_pass_cutoff_hz: float = 25.0,
    dynamic_eq_reduction_db: float = 0.0,
    bass_control_reduction_db: float = 0.0,
    de_esser_reduction_db: float = 0.0,
    saturation_amount: float = 0.0,
) -> dict[str, object]:
    """Sign internal MinIO objects, then delegate processing to RunPod."""
    storage = MinioSignedUrlService.from_environment()
    storage.ensure_bucket()
    transfer = storage.create_transfer(source_object, destination_object)
    return cast(
        dict[str, object],
        remote_master_audio.run(
            transfer.source_url,
            transfer.destination_url,
            source_sha256,
            target_lufs,
            maximum_gain_adjustment_db,
            ceiling_dbfs,
            bit_depth,
            eq_low_gain_db,
            eq_mid_gain_db,
            eq_high_gain_db,
            clipper_drive_db,
            limiter_lookahead_ms,
            limiter_release_ms,
            high_pass_enabled,
            high_pass_cutoff_hz,
            dynamic_eq_reduction_db,
            bass_control_reduction_db,
            de_esser_reduction_db,
            saturation_amount,
        ),
    )


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


def _sha256_file(path: Path) -> str:
    """Hash one worker-local file without retaining it in memory."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _master_filename(job: AnalysisJobRecord) -> str:
    """Build one retry-stable, browser-safe master name from the source contract."""
    stem = (
        re.sub(r"[^A-Za-z0-9._-]+", "-", Path(job.original_filename).stem).strip("-._") or "track"
    )
    created_at = job.created_at
    if created_at is None:
        raise ValueError("Job creation timestamp is required for master naming")
    timestamp = created_at.strftime("%Y%m%dT%H%M%SZ")
    return f"{stem}-{job.bit_depth}bit-openmaster-{timestamp}.wav"


def _job_policy(job: AnalysisJobRecord) -> MasteringPolicy:
    """Build the explicit baseline policy persisted with one job."""
    return MasteringPolicy(
        target_lufs=job.target_lufs,
        maximum_gain_adjustment_db=job.maximum_gain_adjustment_db,
        ceiling_dbfs=job.ceiling_dbfs,
        eq_low_gain_db=job.eq_low_gain_db,
        eq_mid_gain_db=job.eq_mid_gain_db,
        eq_high_gain_db=job.eq_high_gain_db,
        clipper_drive_db=job.clipper_drive_db,
        limiter_lookahead_ms=job.limiter_lookahead_ms,
        limiter_release_ms=job.limiter_release_ms,
        high_pass_enabled=job.high_pass_enabled,
        high_pass_cutoff_hz=job.high_pass_cutoff_hz,
        dynamic_eq_reduction_db=job.dynamic_eq_reduction_db,
        bass_control_reduction_db=job.bass_control_reduction_db,
        de_esser_reduction_db=job.de_esser_reduction_db,
        saturation_amount=job.saturation_amount,
    )


def _waveform_list(value: object) -> list[float]:
    """Validate the small waveform document returned across the RunPod boundary."""
    if not isinstance(value, list) or not 16 <= len(value) <= 2048:
        raise ValueError("RunPod waveform output is invalid")
    points = [float(point) for point in value]
    if any(point < 0.0 or point > 1.0 for point in points):
        raise ValueError("RunPod waveform points are outside [0, 1]")
    return points


def _visualization_list(value: object) -> list[float]:
    """Validate a normalized compact visualization returned by RunPod."""
    return _waveform_list(value)
