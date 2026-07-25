"""Secure RunPod handler for signed-URL deterministic mastering jobs."""

from __future__ import annotations

import hashlib
import http.client
import os
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from urllib.request import urlopen

from packages.analysis_engine import AnalysisService
from packages.audio_core import decode_audio, waveform_envelope
from packages.dsp_engine import AutomaticMasteringService, MasteringPolicy
from packages.remote_compute import RemoteMasteringRequest

_CHUNK_SIZE = 1024 * 1024


def _allowed_hosts() -> frozenset[str]:
    return frozenset(
        host.strip().lower()
        for host in os.environ.get("OPENMASTER_ALLOWED_STORAGE_HOSTS", "").split(",")
        if host.strip()
    )


def _validate_storage_host(url: str) -> None:
    allowed = _allowed_hosts()
    hostname = (urlsplit(url).hostname or "").lower()
    if not allowed:
        raise ValueError("OPENMASTER_ALLOWED_STORAGE_HOSTS must not be empty")
    if hostname not in allowed:
        raise ValueError("Signed URL host is not allowed")


def _download(url: str, destination: Path, maximum_bytes: int) -> str:
    _validate_storage_host(url)
    digest = hashlib.sha256()
    total = 0
    with urlopen(url, timeout=60) as response, destination.open("wb") as output:  # noqa: S310
        while chunk := response.read(_CHUNK_SIZE):
            total += len(chunk)
            if total > maximum_bytes:
                raise ValueError("Remote source exceeds OPENMASTER_MAX_REMOTE_BYTES")
            digest.update(chunk)
            output.write(chunk)
    return digest.hexdigest()


def _upload(url: str, source: Path) -> None:
    _validate_storage_host(url)
    parsed = urlsplit(url)
    hostname = parsed.hostname
    if hostname is None:  # pragma: no cover - already enforced by host validation
        raise ValueError("Signed destination URL must contain a hostname")
    connection = http.client.HTTPSConnection(hostname, parsed.port or 443, timeout=300)
    path = parsed.path + (f"?{parsed.query}" if parsed.query else "")
    connection.putrequest("PUT", path)
    connection.putheader("Content-Type", "audio/wav")
    connection.putheader("Content-Length", str(source.stat().st_size))
    connection.endheaders()
    with source.open("rb") as stream:
        while chunk := stream.read(_CHUNK_SIZE):
            connection.send(chunk)
    response = connection.getresponse()
    response.read()
    connection.close()
    if response.status < 200 or response.status >= 300:
        raise OSError(f"Signed destination upload failed with HTTP {response.status}")


def handler(event: dict[str, Any]) -> dict[str, object]:
    """Download, verify, master, and upload one immutable audio object."""
    raw_input = event.get("input")
    if not isinstance(raw_input, dict):
        raise ValueError("RunPod event input must be an object")
    request = RemoteMasteringRequest(**raw_input)
    maximum_bytes = int(os.environ.get("OPENMASTER_MAX_REMOTE_BYTES", "2147483648"))

    with tempfile.TemporaryDirectory(prefix="openmaster-") as workspace:
        suffix = Path(urlsplit(request.source_url).path).suffix.lower()
        if suffix not in {
            ".wav",
            ".wave",
            ".aiff",
            ".aif",
            ".flac",
            ".m4a",
            ".mp3",
            ".ogg",
            ".opus",
        }:
            raise ValueError("Signed source URL must retain a supported audio extension")
        source = Path(workspace) / f"source{suffix}"
        destination = Path(workspace) / "master.wav"
        actual_digest = _download(request.source_url, source, maximum_bytes)
        if actual_digest != request.source_sha256:
            raise ValueError("Downloaded source SHA-256 does not match the job contract")

        decoded = decode_audio(source)
        analysis = AnalysisService().analyze_decoded(decoded)
        service = AutomaticMasteringService(
            MasteringPolicy(
                target_lufs=request.target_lufs,
                maximum_gain_adjustment_db=request.maximum_gain_adjustment_db,
                ceiling_dbfs=request.ceiling_dbfs,
            )
        )
        result = service.master_to_wav(
            decoded.samples,
            decoded.metadata.sample_rate_hz,
            analysis,
            destination,
            bit_depth=request.bit_depth,
        )
        _upload(request.destination_url, result.output_path)
        return {
            "source_sha256": actual_digest,
            "analysis": analysis.to_dict(),
            "decision": asdict(result.mastering.decision),
            "processors": list(result.mastering.render.applied_processors),
            "source_waveform": waveform_envelope(decoded.samples),
            "master_waveform": waveform_envelope(result.mastering.render.samples),
        }


def main() -> None:
    """Start the queue-based RunPod worker."""
    import runpod  # type: ignore[import-not-found]

    runpod.serverless.start({"handler": handler})


if __name__ == "__main__":
    main()
