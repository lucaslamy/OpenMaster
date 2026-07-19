"""Tests for production health endpoints used by Kubernetes probes."""

from fastapi.testclient import TestClient

from apps.api.main import app


def test_health_endpoints_are_available_without_external_dependencies() -> None:
    client = TestClient(app)

    assert client.get("/health/live").json() == {"status": "live"}
    assert client.get("/health/ready").json() == {"status": "ready"}
