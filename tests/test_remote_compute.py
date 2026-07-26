"""Tests for bounded RunPod contracts without network or cloud credentials."""

from __future__ import annotations

import json
from urllib.request import Request

import pytest

from packages.remote_compute import (
    RemoteComputeError,
    RemoteMasteringRequest,
    RunPodClient,
    RunPodJobStatus,
)


def _request() -> RemoteMasteringRequest:
    return RemoteMasteringRequest(
        source_url="https://objects.example.com/input.wav?signature=source",
        destination_url="https://objects.example.com/output.wav?signature=destination",
        source_sha256="a" * 64,
    )


def test_remote_contract_rejects_insecure_urls_and_invalid_digest() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        RemoteMasteringRequest(
            source_url="http://objects.example.com/input.wav",
            destination_url="https://objects.example.com/output.wav",
            source_sha256="a" * 64,
        )
    with pytest.raises(ValueError, match="SHA-256"):
        RemoteMasteringRequest(
            source_url="https://objects.example.com/input.wav",
            destination_url="https://objects.example.com/output.wav",
            source_sha256="not-a-digest",
        )


def test_client_submits_async_job_without_api_key_in_payload() -> None:
    captured: list[Request] = []

    def transport(request: Request, timeout: float) -> bytes:
        captured.append(request)
        assert timeout == 30.0
        return json.dumps({"id": "job-123", "status": "IN_QUEUE"}).encode()

    client = RunPodClient("endpoint-123", "secret-api-key", transport=transport)
    result = client.submit_mastering(_request())

    assert result.id == "job-123"
    assert result.status is RunPodJobStatus.IN_QUEUE
    assert captured[0].full_url.endswith("/endpoint-123/run")
    payload = captured[0].data or b""
    assert b"secret-api-key" not in payload
    submitted = json.loads(payload)["input"]
    assert submitted["source_sha256"] == "a" * 64
    assert submitted["maximum_gain_adjustment_db"] == 12.0
    assert submitted["ceiling_dbfs"] == -1.0
    assert submitted["eq_low_gain_db"] == 0.0
    assert submitted["clipper_drive_db"] == 0.0
    assert submitted["limiter_lookahead_ms"] == 3.0
    assert submitted["limiter_release_ms"] == 80.0
    assert submitted["high_pass_enabled"] is True
    assert submitted["high_pass_cutoff_hz"] == 25.0
    assert submitted["dynamic_eq_reduction_db"] == 0.0
    assert submitted["bass_control_reduction_db"] == 0.0
    assert submitted["de_esser_reduction_db"] == 0.0
    assert submitted["saturation_amount"] == 0.0
    assert captured[0].headers["Authorization"] == "Bearer secret-api-key"


def test_client_waits_for_completion() -> None:
    responses = iter(
        (
            {"id": "job-123", "status": "IN_PROGRESS"},
            {"id": "job-123", "status": "COMPLETED", "output": {"processors": ["gain"]}},
        )
    )

    def transport(request: Request, timeout: float) -> bytes:
        return json.dumps(next(responses)).encode()

    client = RunPodClient("endpoint-123", "key", transport=transport)
    result = client.wait("job-123", sleeper=lambda _: None)

    assert result.output == {"processors": ["gain"]}


def test_client_surfaces_remote_failure() -> None:
    def transport(request: Request, timeout: float) -> bytes:
        return json.dumps({"id": "job-123", "status": "FAILED", "error": "worker failed"}).encode()

    client = RunPodClient("endpoint-123", "key", transport=transport)
    with pytest.raises(RemoteComputeError, match="worker failed"):
        client.wait("job-123", sleeper=lambda _: None)
