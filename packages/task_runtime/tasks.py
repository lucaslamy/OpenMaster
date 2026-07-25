"""Retry-safe local task implementations used by dedicated Celery queues."""

from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import cast

from packages.analysis_engine import AnalysisResult, AnalysisService
from packages.audio_core import decode_audio, encode_wav
from packages.database import AnalysisJobRepository
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
    output_object = f"mastering/{job_id}/master-{job.bit_depth}bit.wav"
    storage = MinioObjectStore.from_environment()
    try:
        with tempfile.TemporaryDirectory(prefix="openmaster-mastering-") as directory:
            suffix = Path(object_name).suffix.lower()
            source = Path(directory) / f"source{suffix}"
            destination = Path(directory) / "master.wav"
            storage.download(object_name, source)
            analysis = AnalysisResult(**job.result)
            recommendation = MasteringAssistant().recommend(
                analysis,
                target_lufs=job.target_lufs,
            )
            if os.environ.get("OPENMASTER_REMOTE_COMPUTE_ENABLED", "false").lower() == "true":
                source_sha256 = _sha256_file(source)
                remote_result = cast(
                    dict[str, object],
                    remote_master_minio_object.run(
                        object_name,
                        output_object,
                        source_sha256,
                        job.target_lufs,
                        job.bit_depth,
                    ),
                )
                mastering_result: dict[str, object] = {
                    "execution": "runpod",
                    **remote_result,
                    "bit_depth": job.bit_depth,
                }
            else:
                decoded = decode_audio(source)
                policy = MasteringPolicy(target_lufs=job.target_lufs)
                mastered = AutomaticMasteringService(policy).master_to_wav(
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
                }
        repository.mark_mastered(
            job_id,
            recommendation=recommendation.to_dict(),
            mastering_result=mastering_result,
            output_object_name=output_object,
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
    bit_depth: int = 24,
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
    bit_depth: int = 24,
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
            bit_depth,
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
