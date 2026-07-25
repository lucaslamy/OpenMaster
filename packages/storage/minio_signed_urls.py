"""Generate short-lived public URLs for objects held by the internal MinIO service."""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Protocol
from urllib.parse import urlsplit


class MinioClient(Protocol):
    """Subset of the MinIO SDK needed by the application."""

    def bucket_exists(self, bucket_name: str) -> bool: ...

    def make_bucket(self, bucket_name: str) -> None: ...

    def presigned_get_object(
        self,
        bucket_name: str,
        object_name: str,
        expires: timedelta,
        response_headers: dict[str, str] | None = None,
    ) -> str: ...

    def presigned_put_object(
        self,
        bucket_name: str,
        object_name: str,
        expires: timedelta,
    ) -> str: ...


@dataclass(frozen=True, slots=True)
class SignedObjectTransfer:
    """One source download URL and one destination upload URL."""

    source_url: str
    destination_url: str
    expires_in_seconds: int


def _endpoint_parts(url: str, *, require_https: bool) -> tuple[str, bool]:
    parsed = urlsplit(url)
    allowed_schemes = {"https"} if require_https else {"http", "https"}
    if (
        parsed.scheme not in allowed_schemes
        or not parsed.hostname
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
    ):
        expected = "an HTTPS origin" if require_https else "an HTTP(S) origin"
        raise ValueError(f"MinIO endpoint must be {expected} without path or credentials")
    endpoint = parsed.hostname
    if parsed.port:
        endpoint = f"{endpoint}:{parsed.port}"
    return endpoint, parsed.scheme == "https"


def _validate_object_name(value: str, field: str) -> None:
    if not value or value.startswith("/") or value.endswith("/") or ".." in value.split("/"):
        raise ValueError(f"{field} must be a non-empty canonical object name")


class MinioSignedUrlService:
    """Use the internal endpoint for administration and the public host for signatures."""

    def __init__(
        self,
        internal_client: MinioClient,
        public_client: MinioClient,
        bucket_name: str,
    ) -> None:
        if not bucket_name or "/" in bucket_name:
            raise ValueError("MinIO bucket name must be non-empty and contain no slash")
        self._internal = internal_client
        self._public = public_client
        self._bucket = bucket_name

    @classmethod
    def from_environment(cls) -> MinioSignedUrlService:
        """Build clients without putting credentials in Helm values."""
        internal_endpoint, internal_secure = _endpoint_parts(
            os.environ["MINIO_INTERNAL_ENDPOINT"],
            require_https=False,
        )
        public_endpoint, public_secure = _endpoint_parts(
            os.environ["MINIO_PUBLIC_ENDPOINT"],
            require_https=True,
        )
        access_key = os.environ["MINIO_ROOT_USER"]
        secret_key = os.environ["MINIO_ROOT_PASSWORD"]
        region = os.environ.get("MINIO_REGION", "us-east-1")
        minio_type: Any = importlib.import_module("minio").Minio
        common = {
            "access_key": access_key,
            "secret_key": secret_key,
            "region": region,
        }
        return cls(
            minio_type(internal_endpoint, secure=internal_secure, **common),
            minio_type(public_endpoint, secure=public_secure, **common),
            os.environ.get("MINIO_BUCKET", "openmaster"),
        )

    def ensure_bucket(self) -> None:
        """Create the private application bucket only when it does not already exist."""
        if not self._internal.bucket_exists(self._bucket):
            self._internal.make_bucket(self._bucket)

    def create_transfer(
        self,
        source_object: str,
        destination_object: str,
        *,
        expires_in_seconds: int = 7200,
    ) -> SignedObjectTransfer:
        """Sign one GET and one PUT against the externally reachable MinIO hostname."""
        _validate_object_name(source_object, "source_object")
        _validate_object_name(destination_object, "destination_object")
        if not 60 <= expires_in_seconds <= 86_400:
            raise ValueError("Signed URL lifetime must be between 60 seconds and 24 hours")
        expires = timedelta(seconds=expires_in_seconds)
        return SignedObjectTransfer(
            source_url=self._public.presigned_get_object(
                self._bucket,
                source_object,
                expires,
            ),
            destination_url=self._public.presigned_put_object(
                self._bucket,
                destination_object,
                expires,
            ),
            expires_in_seconds=expires_in_seconds,
        )

    def create_download_url(
        self,
        object_name: str,
        *,
        expires_in_seconds: int = 900,
        download_name: str | None = None,
    ) -> str:
        """Sign a short-lived public GET for a completed private object."""
        _validate_object_name(object_name, "object_name")
        if download_name is not None and (
            not download_name
            or "/" in download_name
            or "\\" in download_name
            or '"' in download_name
            or "\r" in download_name
            or "\n" in download_name
        ):
            raise ValueError("download_name must be a safe basename")
        if not 60 <= expires_in_seconds <= 86_400:
            raise ValueError("Signed URL lifetime must be between 60 seconds and 24 hours")
        return self._public.presigned_get_object(
            self._bucket,
            object_name,
            timedelta(seconds=expires_in_seconds),
            (
                {"response-content-disposition": f'attachment; filename="{download_name}"'}
                if download_name is not None
                else None
            ),
        )
