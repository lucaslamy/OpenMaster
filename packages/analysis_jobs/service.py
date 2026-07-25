"""Coordinate validated uploads, durable jobs, and Celery dispatch."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

from packages.audio_core import SUPPORTED_AUDIO_SUFFIXES
from packages.database import AnalysisJobRecord, AnalysisJobRepository
from packages.storage import MinioObjectStore, MinioSignedUrlService


class InvalidUploadError(ValueError):
    """Raised before unsupported or oversized data reaches object storage."""


class AnalysisJobService:
    """Create idempotent jobs and expose their durable public state."""

    def __init__(
        self,
        repository: AnalysisJobRepository,
        storage: MinioObjectStore,
        enqueue: Callable[[str, str], None],
        *,
        maximum_upload_bytes: int,
        signed_urls: MinioSignedUrlService | None = None,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._enqueue = enqueue
        self._maximum_upload_bytes = maximum_upload_bytes
        self._signed_urls = signed_urls

    @classmethod
    def from_environment(cls) -> AnalysisJobService:
        """Build production adapters lazily after the API process has started."""
        from packages.task_runtime.tasks import analyze_minio_object

        public_endpoint = os.environ.get("MINIO_PUBLIC_ENDPOINT")
        return cls(
            AnalysisJobRepository.from_environment(),
            MinioObjectStore.from_environment(),
            lambda job_id, object_name: analyze_minio_object.apply_async(
                args=(job_id, object_name),
                queue="analysis",
            ),
            maximum_upload_bytes=int(os.environ.get("MAX_UPLOAD_BYTES", "2147483648")),
            signed_urls=MinioSignedUrlService.from_environment() if public_endpoint else None,
        )

    def submit(
        self,
        *,
        filename: str,
        content_type: str,
        stream: BinaryIO,
        length: int,
        idempotency_key: str,
        target_lufs: float = -14.0,
        bit_depth: int = 24,
    ) -> AnalysisJobRecord:
        """Validate, store, persist, and enqueue one upload exactly once."""
        key = idempotency_key.strip()
        if not key or len(key) > 255:
            raise InvalidUploadError("Idempotency-Key must contain between 1 and 255 characters")
        existing = self._repository.get_by_idempotency_key(key)
        if existing is not None:
            if existing.status == "queued":
                self._enqueue(existing.id, existing.object_name)
            return existing
        safe_filename = Path(filename or "").name
        suffix = Path(safe_filename).suffix.lower()
        if suffix not in SUPPORTED_AUDIO_SUFFIXES:
            raise InvalidUploadError("Unsupported audio format")
        if length <= 0:
            raise InvalidUploadError("Uploaded audio file is empty")
        if length > self._maximum_upload_bytes:
            raise InvalidUploadError("Uploaded audio file exceeds MAX_UPLOAD_BYTES")
        if not -24.0 <= target_lufs <= -8.0:
            raise InvalidUploadError("target_lufs must be between -24 and -8")
        if bit_depth not in {16, 24, 32}:
            raise InvalidUploadError("bit_depth must be 16, 24, or 32")

        job_id = str(uuid4())
        object_name = f"analysis/{job_id}/source{suffix}"
        self._storage.upload(
            object_name,
            stream,
            length=length,
            content_type=content_type,
        )
        job, created = self._repository.create_or_get(
            job_id=job_id,
            idempotency_key=key,
            object_name=object_name,
            original_filename=safe_filename,
            target_lufs=target_lufs,
            bit_depth=bit_depth,
        )
        if created or job.status == "queued":
            self._enqueue(job.id, job.object_name)
        return job

    def get(self, job_id: str) -> AnalysisJobRecord | None:
        """Return one job without leaking its internal object name."""
        return self._repository.get(job_id)

    def create_download_url(self, job_id: str) -> str | None:
        """Return a short-lived download URL only for a completed master."""
        job = self._repository.get(job_id)
        if job is None or job.output_object_name is None:
            return None
        if self._signed_urls is None:
            raise RuntimeError("Public MinIO signing is not configured")
        return self._signed_urls.create_download_url(job.output_object_name)
