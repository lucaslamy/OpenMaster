"""Idempotent Celery runtime with lazy application loading."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from celery import Celery

    celery_app: Celery

__all__ = ["celery_app"]


def __getattr__(name: str) -> Any:
    """Load Celery only when callers explicitly request the application."""
    if name != "celery_app":
        raise AttributeError(name)
    from .celery_app import celery_app

    return celery_app
