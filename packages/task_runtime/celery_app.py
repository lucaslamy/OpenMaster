"""Celery application configured exclusively from runtime environment variables."""

from __future__ import annotations

import os

from celery import Celery

celery_app = Celery("openmaster")
celery_app.conf.update(
    broker_url=os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0"),
    result_backend=os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/1"),
    task_default_queue="analysis",
    task_routes={
        "openmaster.analysis": {"queue": "analysis"},
        "openmaster.mastering": {"queue": "mastering"},
        "openmaster.remote_mastering": {"queue": "mastering"},
        "openmaster.export": {"queue": "export"},
    },
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
)

from . import tasks as _tasks  # noqa: E402,F401
