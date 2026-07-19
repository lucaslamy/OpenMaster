"""Idempotent Celery task runtime for OpenMaster production workers."""

from .celery_app import celery_app

__all__ = ["celery_app"]
