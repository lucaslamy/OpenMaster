"""Tests for MinIO signed transfers used by RunPod."""

from __future__ import annotations

from datetime import timedelta

import pytest

from packages.storage import MinioSignedUrlService


class FakeMinioClient:
    """Record bucket and signing operations without network access."""

    def __init__(self, *, bucket_exists: bool = True) -> None:
        self.exists = bucket_exists
        self.created: list[str] = []

    def bucket_exists(self, bucket_name: str) -> bool:
        return self.exists

    def make_bucket(self, bucket_name: str) -> None:
        self.created.append(bucket_name)

    def presigned_get_object(
        self,
        bucket_name: str,
        object_name: str,
        expires: timedelta,
    ) -> str:
        return f"https://s3.example.com/{bucket_name}/{object_name}?get={expires.seconds}"

    def presigned_put_object(
        self,
        bucket_name: str,
        object_name: str,
        expires: timedelta,
    ) -> str:
        return f"https://s3.example.com/{bucket_name}/{object_name}?put={expires.seconds}"


def test_service_creates_private_bucket_and_public_signed_transfer() -> None:
    internal = FakeMinioClient(bucket_exists=False)
    public = FakeMinioClient()
    service = MinioSignedUrlService(internal, public, "openmaster")

    service.ensure_bucket()
    transfer = service.create_transfer(
        "input/mix.wav",
        "output/master.wav",
        expires_in_seconds=3600,
    )

    assert internal.created == ["openmaster"]
    assert transfer.source_url == "https://s3.example.com/openmaster/input/mix.wav?get=3600"
    assert transfer.destination_url == (
        "https://s3.example.com/openmaster/output/master.wav?put=3600"
    )


@pytest.mark.parametrize("object_name", ["", "/absolute.wav", "../escape.wav", "folder/"])
def test_service_rejects_unsafe_object_names(object_name: str) -> None:
    service = MinioSignedUrlService(FakeMinioClient(), FakeMinioClient(), "openmaster")
    with pytest.raises(ValueError):
        service.create_transfer(object_name, "output/master.wav")
