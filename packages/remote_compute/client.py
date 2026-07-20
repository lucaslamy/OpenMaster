"""Small dependency-free client for queue-based RunPod Serverless endpoints."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, cast
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .models import RemoteMasteringRequest

JsonObject = dict[str, Any]
Transport = Callable[[Request, float], bytes]


class RemoteComputeError(RuntimeError):
    """Raised for an invalid or failed RunPod operation."""


class RunPodJobStatus(StrEnum):
    """RunPod queue states relevant to OpenMaster."""

    IN_QUEUE = "IN_QUEUE"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMED_OUT = "TIMED_OUT"


@dataclass(frozen=True, slots=True)
class RunPodJob:
    """Validated status returned by RunPod."""

    id: str
    status: RunPodJobStatus
    output: JsonObject | None = None
    error: str | None = None


def _default_transport(request: Request, timeout: float) -> bytes:
    with urlopen(request, timeout=timeout) as response:  # noqa: S310
        return cast(bytes, response.read())


class RunPodClient:
    """Submit and monitor asynchronous jobs without exposing the API key."""

    def __init__(
        self,
        endpoint_id: str,
        api_key: str,
        *,
        base_url: str = "https://api.runpod.ai/v2",
        request_timeout_seconds: float = 30.0,
        transport: Transport = _default_transport,
    ) -> None:
        if not endpoint_id or "/" in endpoint_id:
            raise ValueError("endpoint_id must be a non-empty RunPod endpoint identifier")
        if not api_key:
            raise ValueError("api_key must not be empty")
        if not base_url.startswith("https://"):
            raise ValueError("base_url must use HTTPS")
        self._endpoint_url = f"{base_url.rstrip('/')}/{endpoint_id}"
        self._api_key = api_key
        self._timeout = request_timeout_seconds
        self._transport = transport

    def submit_mastering(
        self,
        job: RemoteMasteringRequest,
        *,
        execution_timeout_ms: int = 3_600_000,
        ttl_ms: int = 7_200_000,
    ) -> RunPodJob:
        """Submit one asynchronous mastering job."""
        if execution_timeout_ms <= 0 or ttl_ms < execution_timeout_ms:
            raise ValueError("ttl_ms must be positive and cover execution_timeout_ms")
        payload = {
            "input": job.to_dict(),
            "policy": {
                "executionTimeout": execution_timeout_ms,
                "ttl": ttl_ms,
            },
        }
        return self._request("POST", "/run", payload)

    def status(self, job_id: str) -> RunPodJob:
        """Read one job without relying on RunPod result retention as storage."""
        return self._request("GET", f"/status/{job_id}")

    def cancel(self, job_id: str) -> RunPodJob:
        """Cancel one queued or running job."""
        return self._request("POST", f"/cancel/{job_id}", {})

    def wait(
        self,
        job_id: str,
        *,
        timeout_seconds: float = 3_900.0,
        poll_interval_seconds: float = 5.0,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> RunPodJob:
        """Poll until completion while enforcing a caller-side deadline."""
        deadline = time.monotonic() + timeout_seconds
        while True:
            job = self.status(job_id)
            if job.status is RunPodJobStatus.COMPLETED:
                return job
            if job.status in {
                RunPodJobStatus.FAILED,
                RunPodJobStatus.CANCELLED,
                RunPodJobStatus.TIMED_OUT,
            }:
                raise RemoteComputeError(job.error or f"RunPod job ended as {job.status}")
            if time.monotonic() >= deadline:
                raise RemoteComputeError("Timed out waiting for RunPod job")
            sleeper(poll_interval_seconds)

    def _request(
        self,
        method: str,
        path: str,
        payload: JsonObject | None = None,
    ) -> RunPodJob:
        data = None if payload is None else json.dumps(payload).encode()
        request = Request(
            f"{self._endpoint_url}{path}",
            data=data,
            method=method,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            raw = self._transport(request, self._timeout)
            document = json.loads(raw)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise RemoteComputeError(f"RunPod request failed: {error}") from error
        if not isinstance(document, dict):
            raise RemoteComputeError("RunPod response must be a JSON object")
        try:
            status = RunPodJobStatus(str(document["status"]))
            job_id = str(document["id"])
        except (KeyError, ValueError) as error:
            raise RemoteComputeError("RunPod response has no valid id/status") from error
        output = document.get("output")
        return RunPodJob(
            id=job_id,
            status=status,
            output=output if isinstance(output, dict) else None,
            error=str(document["error"]) if document.get("error") else None,
        )
