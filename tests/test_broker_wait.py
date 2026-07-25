"""Tests for bounded worker broker startup."""

from __future__ import annotations

import subprocess
import sys
from contextlib import nullcontext

from packages.task_runtime import wait_for_broker


def test_wait_for_broker_uses_configured_redis_host(monkeypatch) -> None:
    attempts: list[tuple[tuple[str, int], int]] = []
    monkeypatch.setenv("CELERY_BROKER_URL", "redis://redis.example:6380/0")
    monkeypatch.setattr(
        wait_for_broker.socket,
        "create_connection",
        lambda address, timeout: (attempts.append((address, timeout)) or nullcontext()),
    )

    wait_for_broker.wait_for_broker()

    assert attempts == [(("redis.example", 6380), 2)]


def test_wait_module_does_not_import_celery_runtime() -> None:
    """The init-container module must not load the audio worker dependency graph."""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "import packages.task_runtime.wait_for_broker; "
                "assert 'celery' not in sys.modules; "
                "assert 'packages.task_runtime.tasks' not in sys.modules"
            ),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
