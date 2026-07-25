"""Private object transfers against the internal MinIO service."""

from __future__ import annotations

import importlib
import os
from pathlib import Path
from typing import Any, BinaryIO, Protocol

from .minio_signed_urls import _endpoint_parts, _validate_object_name


class ObjectResponse(Protocol):
    """Streaming response returned by the MinIO SDK."""

    def stream(self, amt: int = 0) -> Any: ...

    def close(self) -> None: ...

    def release_conn(self) -> None: ...


class InternalMinioClient(Protocol):
    """MinIO SDK subset required for private application transfers."""

    def bucket_exists(self, bucket_name: str) -> bool: ...

    def make_bucket(self, bucket_name: str) -> None: ...

    def put_object(
        self,
        bucket_name: str,
        object_name: str,
        data: BinaryIO,
        length: int,
        content_type: str,
    ) -> Any: ...

    def get_object(self, bucket_name: str, object_name: str) -> ObjectResponse: ...


class MinioObjectStore:
    """Upload and download immutable objects through the cluster-local endpoint."""

    def __init__(self, client: InternalMinioClient, bucket_name: str) -> None:
        if not bucket_name or "/" in bucket_name:
            raise ValueError("MinIO bucket name must be non-empty and contain no slash")
        self._client = client
        self._bucket = bucket_name

    @classmethod
    def from_environment(cls) -> MinioObjectStore:
        """Build the internal client from runtime configuration and credentials."""
        endpoint, secure = _endpoint_parts(
            os.environ["MINIO_INTERNAL_ENDPOINT"],
            require_https=False,
        )
        minio_type: Any = importlib.import_module("minio").Minio
        client = minio_type(
            endpoint,
            access_key=os.environ["MINIO_ROOT_USER"],
            secret_key=os.environ["MINIO_ROOT_PASSWORD"],
            region=os.environ.get("MINIO_REGION", "us-east-1"),
            secure=secure,
        )
        return cls(client, os.environ.get("MINIO_BUCKET", "openmaster"))

    def ensure_bucket(self) -> None:
        """Create the application bucket if it is absent."""
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)

    def upload(
        self,
        object_name: str,
        stream: BinaryIO,
        *,
        length: int,
        content_type: str,
    ) -> None:
        """Upload one bounded stream under a canonical object name."""
        _validate_object_name(object_name, "object_name")
        if length < 0:
            raise ValueError("Object length cannot be negative")
        self.ensure_bucket()
        self._client.put_object(
            self._bucket,
            object_name,
            stream,
            length,
            content_type or "application/octet-stream",
        )

    def download(self, object_name: str, destination: Path) -> None:
        """Stream one private object to a worker-local temporary file."""
        _validate_object_name(object_name, "object_name")
        response = self._client.get_object(self._bucket, object_name)
        try:
            with destination.open("wb") as output:
                for chunk in response.stream(1024 * 1024):
                    output.write(chunk)
        finally:
            response.close()
            response.release_conn()
