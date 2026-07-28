"""Tests for production health endpoints used by Kubernetes probes."""

import asyncio

from httpx import ASGITransport, AsyncClient

from apps.api.main import app


def test_health_endpoints_are_available_without_external_dependencies() -> None:
    async def request_probes() -> tuple[dict[str, str], dict[str, str]]:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://openmaster.test",
        ) as client:
            live = await client.get("/health/live")
            ready = await client.get("/health/ready")
            return live.json(), ready.json()

    live, ready = asyncio.run(request_probes())

    assert live == {"status": "live"}
    assert ready == {"status": "ready"}
