"""HTTP routes for durable asynchronous audio-analysis jobs."""

from __future__ import annotations

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
    error_code: str | None = None
    error_message: str | None = None


@lru_cache(maxsize=1)
def get_analysis_job_service() -> AnalysisJobService:
    """Build production adapters once per API process."""
    return AnalysisJobService.from_environment()


@router.post(
    "/analysis-jobs",
    response_model=AnalysisJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_analysis_job(
    file: UploadFile,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key")],
    service: Annotated[AnalysisJobService, Depends(get_analysis_job_service)],
    target_lufs: Annotated[float, Form()] = -14.0,
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
        error_code=job.error_code,
        error_message=job.error_message,
    )
