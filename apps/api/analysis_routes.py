"""HTTP routes for durable asynchronous audio-analysis jobs."""

from __future__ import annotations

import hmac
import os
import secrets
import time
from base64 import urlsafe_b64encode
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
    status: Literal[
        "queued", "running", "analyzed", "mastering", "retry_wait", "succeeded", "failed"
    ]
    original_filename: str
    project_name: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    result: dict[str, Any] | None = None
    recommendation: dict[str, Any] | None = None
    mastering_result: dict[str, Any] | None = None
    download_url: str | None = None
    preview_url: str | None = None
    initial_preview_url: str | None = None
    source_waveform: list[float] | None = None
    master_waveform: list[float] | None = None
    source_spectrum: list[float] | None = None
    master_spectrum: list[float] | None = None
    source_level_timeline: list[float] | None = None
    master_level_timeline: list[float] | None = None
    error_code: str | None = None
    error_message: str | None = None
    parent_job_id: str | None = None
    interactive_settings: dict[str, Any] | None = None
    source_preview_url: str | None = None


class MasteringSettingsRequest(BaseModel):
    """Bounded settings are validated by the service shared with job creation."""

    settings: dict[str, float | int | bool]


class ProjectRenameRequest(BaseModel):
    """Editable metadata for a retained project."""

    name: str


class MasteringAccessRequest(BaseModel):
    """Password sent alone before any potentially large upload."""

    password: str


class MasteringAccessResponse(BaseModel):
    """Short-lived proof accepted by protected mastering operations."""

    token: str
    expires_in_seconds: int


@lru_cache(maxsize=1)
def get_analysis_job_service() -> AnalysisJobService:
    """Build production adapters once per API process."""
    return AnalysisJobService.from_environment()


def verify_mastering_access(
    password: str | None,
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


def create_mastering_token(password: str | None) -> MasteringAccessResponse:
    """Validate the shared password and issue a short-lived signed proof."""
    verify_mastering_access(password)
    configured = os.environ["MASTERING_ACCESS_PASSWORD"]
    expires_in_seconds = 60
    expires_at = int(time.time()) + expires_in_seconds
    nonce = secrets.token_urlsafe(18)
    payload = f"{expires_at}.{nonce}"
    signature = (
        urlsafe_b64encode(hmac.digest(configured.encode(), payload.encode(), "sha256"))
        .decode()
        .rstrip("=")
    )
    return MasteringAccessResponse(
        token=f"{payload}.{signature}",
        expires_in_seconds=expires_in_seconds,
    )


def verify_mastering_token(token: str | None) -> None:
    """Reject missing, expired, malformed, or forged mastering proofs."""
    configured = os.environ.get("MASTERING_ACCESS_PASSWORD")
    if not configured:
        raise HTTPException(status_code=503, detail="Mastering access is not configured")
    try:
        expires, nonce, signature = (token or "").split(".", 2)
        expires_at = int(expires)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Mastering authorization is invalid") from None
    payload = f"{expires_at}.{nonce}"
    expected = (
        urlsafe_b64encode(hmac.digest(configured.encode(), payload.encode(), "sha256"))
        .decode()
        .rstrip("=")
    )
    if expires_at < int(time.time()) or not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Mastering authorization is invalid")


@router.post("/mastering-access", response_model=MasteringAccessResponse)
def authorize_mastering(request: MasteringAccessRequest) -> MasteringAccessResponse:
    """Validate only the password so failures return before an upload starts."""
    return create_mastering_token(request.password)


@router.post(
    "/analysis-jobs",
    response_model=AnalysisJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_analysis_job(
    file: UploadFile,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    service: Annotated[AnalysisJobService, Depends(get_analysis_job_service)],
    mastering_authorization: Annotated[
        str | None, Header(alias="X-Mastering-Authorization")
    ] = None,
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
    ai_assist_enabled: Annotated[bool, Form()] = False,
    bit_depth: Annotated[int, Form()] = 24,
) -> AnalysisJobResponse:
    """Store one supported audio upload and queue its deterministic analysis."""
    verify_mastering_token(mastering_authorization)
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
            ai_assist_enabled=ai_assist_enabled,
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


@router.put("/analysis-jobs/{job_id}/settings", response_model=AnalysisJobResponse)
def save_mastering_settings(
    job_id: str,
    request: MasteringSettingsRequest,
    service: Annotated[AnalysisJobService, Depends(get_analysis_job_service)],
) -> AnalysisJobResponse:
    """Persist preview settings; this endpoint never dispatches audio work."""
    job = service.save_settings(job_id, request.settings)
    if job is None:
        raise HTTPException(status_code=404, detail="Analysis job not found")
    return _response(job)


@router.post(
    "/analysis-jobs/{job_id}/master",
    response_model=AnalysisJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def start_initial_master(
    job_id: str,
    request: MasteringSettingsRequest,
    service: Annotated[AnalysisJobService, Depends(get_analysis_job_service)],
) -> AnalysisJobResponse:
    """Commit pre-master settings and enter mastering without repeating analysis."""
    try:
        job = service.start_master(job_id, request.settings)
    except InvalidUploadError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if job is None:
        raise HTTPException(status_code=404, detail="Analysis job not found")
    return _response(job)


@router.get("/analysis-jobs", response_model=list[AnalysisJobResponse])
def list_analysis_jobs(
    service: Annotated[AnalysisJobService, Depends(get_analysis_job_service)],
) -> list[AnalysisJobResponse]:
    """Return the twenty newest retained root projects."""
    return [_response(job) for job in service.list_recent(20)]


@router.patch("/analysis-jobs/{job_id}", response_model=AnalysisJobResponse)
def rename_analysis_project(
    job_id: str,
    request: ProjectRenameRequest,
    service: Annotated[AnalysisJobService, Depends(get_analysis_job_service)],
) -> AnalysisJobResponse:
    """Rename a project without touching its immutable source audio."""
    try:
        job = service.rename_project(job_id, request.name)
    except InvalidUploadError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    if job is None:
        raise HTTPException(status_code=404, detail="Analysis job not found")
    return _response(job)


@router.post(
    "/analysis-jobs/{job_id}/final-renders",
    response_model=AnalysisJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_final_render(
    job_id: str,
    request: MasteringSettingsRequest,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    service: Annotated[AnalysisJobService, Depends(get_analysis_job_service)],
    mastering_authorization: Annotated[
        str | None, Header(alias="X-Mastering-Authorization")
    ] = None,
) -> AnalysisJobResponse:
    """Authorize and dispatch a final render while reusing source and analysis."""
    verify_mastering_token(mastering_authorization)
    try:
        job = service.render_final(job_id, request.settings, idempotency_key)
    except InvalidUploadError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    if job is None:
        raise HTTPException(status_code=404, detail="Analysis job not found")
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


@router.get("/analysis-jobs/{job_id}/initial-preview", response_class=RedirectResponse)
def preview_initial_master(
    job_id: str,
    service: Annotated[AnalysisJobService, Depends(get_analysis_job_service)],
) -> RedirectResponse:
    """Redirect final-render children to their immutable initial master."""
    url = service.create_initial_preview_url(job_id)
    if url is None:
        raise HTTPException(status_code=409, detail="Initial master is not available")
    return RedirectResponse(url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get("/analysis-jobs/{job_id}/source", response_class=RedirectResponse)
def preview_source(
    job_id: str,
    service: Annotated[AnalysisJobService, Depends(get_analysis_job_service)],
) -> RedirectResponse:
    """Redirect to the retained project source for live pre-master audition."""
    url = service.create_source_preview_url(job_id)
    if url is None:
        raise HTTPException(status_code=404, detail="Analysis job not found")
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
        original_filename=job.original_filename,
        project_name=job.project_name,
        created_at=job.created_at.isoformat() if job.created_at else None,
        updated_at=job.updated_at.isoformat() if job.updated_at else None,
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
        initial_preview_url=(
            f"/api/v1/analysis-jobs/{job.id}/initial-preview"
            if job.initial_output_object_name is not None
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
        parent_job_id=job.parent_job_id,
        interactive_settings=job.interactive_settings
        or {
            "target_lufs": job.target_lufs,
            "maximum_gain_adjustment_db": job.maximum_gain_adjustment_db,
            "ceiling_dbfs": job.ceiling_dbfs,
            "eq_low_gain_db": job.eq_low_gain_db,
            "eq_mid_gain_db": job.eq_mid_gain_db,
            "eq_high_gain_db": job.eq_high_gain_db,
            "clipper_drive_db": job.clipper_drive_db,
            "limiter_lookahead_ms": job.limiter_lookahead_ms,
            "limiter_release_ms": job.limiter_release_ms,
            "high_pass_enabled": job.high_pass_enabled,
            "high_pass_cutoff_hz": job.high_pass_cutoff_hz,
            "dynamic_eq_reduction_db": job.dynamic_eq_reduction_db,
            "bass_control_reduction_db": job.bass_control_reduction_db,
            "de_esser_reduction_db": job.de_esser_reduction_db,
            "saturation_amount": job.saturation_amount,
            "ai_assist_enabled": job.ai_assist_enabled,
            "bit_depth": job.bit_depth,
        },
        source_preview_url=f"/api/v1/analysis-jobs/{job.id}/source",
    )
