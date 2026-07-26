"""HTTP routes for durable asynchronous audio-analysis jobs."""

from __future__ import annotations

import hmac
import os
from functools import lru_cache
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Form, Header, HTTPException, UploadFile, status
from pydantic import BaseModel
from starlette.responses import RedirectResponse

from packages.analysis_jobs import AnalysisJobService, InvalidUploadError
from packages.database import AnalysisJobRecord

router = APIRouter(prefix="/api/v1", tags=["analysis"])


class AnalysisJobResponse(BaseModel):
    """Public job state polled by the web application."""

    id: str
    status: Literal["queued", "running", "mastering", "retry_wait", "succeeded", "failed"]
    result: dict[str, Any] | None = None
    recommendation: dict[str, Any] | None = None
    mastering_result: dict[str, Any] | None = None
    download_url: str | None = None
    preview_url: str | None = None
    source_waveform: list[float] | None = None
    master_waveform: list[float] | None = None
    source_spectrum: list[float] | None = None
    master_spectrum: list[float] | None = None
    source_level_timeline: list[float] | None = None
    master_level_timeline: list[float] | None = None
    error_code: str | None = None
    error_message: str | None = None


@lru_cache(maxsize=1)
def get_analysis_job_service() -> AnalysisJobService:
    """Build production adapters once per API process."""
    return AnalysisJobService.from_environment()


def verify_mastering_access(
    password: Annotated[str | None, Header(alias="X-Mastering-Password")] = None,
) -> None:
    """Reject mastering submissions unless the configured shared secret matches."""
    configured = os.environ.get("MASTERING_ACCESS_PASSWORD")
    if not configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mastering access is not configured",
        )
    if password is None or not hmac.compare_digest(password, configured):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid mastering password",
            headers={"WWW-Authenticate": "MasteringPassword"},
        )


@router.post(
    "/analysis-jobs",
    response_model=AnalysisJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_analysis_job(
    file: UploadFile,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    service: Annotated[AnalysisJobService, Depends(get_analysis_job_service)],
    _: Annotated[None, Depends(verify_mastering_access)],
    target_lufs: Annotated[float, Form()] = -14.0,
    maximum_gain_adjustment_db: Annotated[float, Form()] = 12.0,
    ceiling_dbfs: Annotated[float, Form()] = -1.0,
    eq_low_gain_db: Annotated[float, Form()] = 0.0,
    eq_mid_gain_db: Annotated[float, Form()] = 0.0,
    eq_high_gain_db: Annotated[float, Form()] = 0.0,
    clipper_drive_db: Annotated[float, Form()] = 0.0,
    limiter_lookahead_ms: Annotated[float, Form()] = 3.0,
    limiter_release_ms: Annotated[float, Form()] = 80.0,
    high_pass_enabled: Annotated[bool, Form()] = True,
    high_pass_cutoff_hz: Annotated[float, Form()] = 25.0,
    dynamic_eq_reduction_db: Annotated[float, Form()] = 0.0,
    bass_control_reduction_db: Annotated[float, Form()] = 0.0,
    de_esser_reduction_db: Annotated[float, Form()] = 0.0,
    saturation_amount: Annotated[float, Form()] = 0.0,
    bit_depth: Annotated[int, Form()] = 24,
) -> AnalysisJobResponse:
    """Store one supported audio upload and queue its deterministic analysis."""
    try:
        length = file.size
        if length is None:
            file.file.seek(0, 2)
            length = file.file.tell()
        file.file.seek(0)
        job = service.submit(
            filename=file.filename or "",
            content_type=file.content_type or "application/octet-stream",
            stream=file.file,
            length=length,
            idempotency_key=idempotency_key,
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
    except InvalidUploadError as error:
        message = str(error)
        code = (
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            if "MAX_UPLOAD_BYTES" in message
            else status.HTTP_422_UNPROCESSABLE_ENTITY
        )
        raise HTTPException(status_code=code, detail=message) from error
    finally:
        await file.close()
    return _response(job)


@router.get("/analysis-jobs/{job_id}/download", response_class=RedirectResponse)
def download_master(
    job_id: str,
    service: Annotated[AnalysisJobService, Depends(get_analysis_job_service)],
) -> RedirectResponse:
    """Redirect an authorized caller to a short-lived private master URL."""
    url = service.create_download_url(job_id)
    if url is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Master is not available",
        )
    return RedirectResponse(url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get("/analysis-jobs/{job_id}/preview", response_class=RedirectResponse)
def preview_master(
    job_id: str,
    service: Annotated[AnalysisJobService, Depends(get_analysis_job_service)],
) -> RedirectResponse:
    """Redirect an authorized caller to a short-lived inline master URL."""
    url = service.create_preview_url(job_id)
    if url is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Master is not available",
        )
    return RedirectResponse(url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get("/analysis-jobs/{job_id}", response_model=AnalysisJobResponse)
def get_analysis_job(
    job_id: str,
    service: Annotated[AnalysisJobService, Depends(get_analysis_job_service)],
) -> AnalysisJobResponse:
    """Return durable state for frontend polling."""
    job = service.get(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis job not found")
    return _response(job)


def _response(job: AnalysisJobRecord) -> AnalysisJobResponse:
    return AnalysisJobResponse(
        id=job.id,
        status=job.status,  # type: ignore[arg-type]
        result=job.result,
        recommendation=job.recommendation,
        mastering_result=job.mastering_result,
        download_url=(
            f"/api/v1/analysis-jobs/{job.id}/download"
            if job.output_object_name is not None
            else None
        ),
        preview_url=(
            f"/api/v1/analysis-jobs/{job.id}/preview"
            if job.output_object_name is not None
            else None
        ),
        source_waveform=job.source_waveform,
        master_waveform=job.master_waveform,
        source_spectrum=job.source_spectrum,
        master_spectrum=job.master_spectrum,
        source_level_timeline=job.source_level_timeline,
        master_level_timeline=job.master_level_timeline,
        error_code=job.error_code,
        error_message=job.error_message,
    )
