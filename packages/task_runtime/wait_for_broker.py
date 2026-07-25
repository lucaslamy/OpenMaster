"""Wait for the configured Celery broker before starting a worker."""

from __future__ import annotations

import os
import socket
import time
from urllib.parse import urlsplit


def wait_for_broker() -> None:
    """Block for a bounded time until the Redis broker accepts TCP connections."""
    parsed = urlsplit(os.environ["CELERY_BROKER_URL"])
    if not parsed.hostname:
        raise ValueError("CELERY_BROKER_URL must contain a hostname")
    port = parsed.port or 6379
    timeout = int(os.environ.get("OPENMASTER_BROKER_WAIT_SECONDS", "300"))
    deadline = time.monotonic() + timeout
    while True:
        try:
            with socket.create_connection((parsed.hostname, port), timeout=2):
                return
        except OSError as error:
            if time.monotonic() >= deadline:
                raise TimeoutError(
                    "Celery broker did not become reachable before timeout"
                ) from error
            time.sleep(2)


if __name__ == "__main__":
    wait_for_broker()
