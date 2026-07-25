"""Tests for bounded worker broker startup."""

from __future__ import annotations

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
