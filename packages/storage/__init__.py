"""Object-storage contracts for internal MinIO and remote compute transfers."""

from .minio_signed_urls import MinioSignedUrlService, SignedObjectTransfer

__all__ = ["MinioSignedUrlService", "SignedObjectTransfer"]
