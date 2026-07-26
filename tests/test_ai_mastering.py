"""Tests for bounded LamAI mastering advice without network access."""

import json
from dataclasses import asdict
from email.message import Message
from urllib.response import addinfourl

import pytest

from packages.ai_mastering import LamAiMasteringClient, LamAiMasteringError
from packages.analysis_engine.models import AnalysisResult
from packages.dsp_engine import MasteringPolicy


class FakeResponse(addinfourl):
    """Context-managed byte response accepted by urllib."""

    def __enter__(self):  # type: ignore[no-untyped-def]
        return self

    def __exit__(self, *_args):  # type: ignore[no-untyped-def]
        self.close()


def _analysis() -> AnalysisResult:
    return AnalysisResult(
        duration_seconds=120,
        sample_rate_hz=48_000,
        bit_depth=24,
        channels=2,
        lufs=-16,
        rms_dbfs=-18,
        peak_dbfs=-3,
        true_peak_dbfs=-2.8,
        dynamic_range_db=8,
        crest_factor_db=10,
        bpm=90,
        musical_key="A minor",
        stereo_width=0.5,
        phase_correlation=0.8,
        spectral_centroid_hz=2_000,
    )


def test_lamai_advice_is_parsed_and_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = asdict(MasteringPolicy())
    settings["target_lufs"] = -12.0
    body = json.dumps(
        {
            "model": "qwen",
            "message": {
                "role": "assistant",
                "content": json.dumps({"settings": settings, "rationale": "Rap équilibré."}),
            },
        }
    ).encode()

    captured = []

    def fake_open(request, **_kwargs):  # type: ignore[no-untyped-def]
        captured.append(request)
        return FakeResponse(__import__("io").BytesIO(body), Message(), "https://lamai/v1/chat")

    monkeypatch.setattr("packages.ai_mastering.client.urlopen", fake_open)

    advice = LamAiMasteringClient("https://lamai.example", "secret").recommend(
        _analysis(), MasteringPolicy()
    )

    assert advice.policy.target_lufs == -12
    assert advice.rationale == "Rap équilibré."
    assert advice.model == "qwen"
    sent = captured[0].data.decode()
    assert "source_url" not in sent
    assert "MINIO" not in sent
    assert captured[0].headers["Authorization"] == "Bearer secret"


def test_lamai_advice_rejects_out_of_bounds_model_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = asdict(MasteringPolicy())
    settings["ceiling_dbfs"] = 1.0
    body = json.dumps(
        {
            "model": "qwen",
            "message": {"content": json.dumps({"settings": settings, "rationale": "unsafe"})},
        }
    ).encode()
    monkeypatch.setattr(
        "packages.ai_mastering.client.urlopen",
        lambda *_args, **_kwargs: FakeResponse(
            __import__("io").BytesIO(body), Message(), "https://lamai/v1/chat"
        ),
    )

    with pytest.raises(LamAiMasteringError, match="invalid"):
        LamAiMasteringClient("https://lamai.example", "secret").recommend(
            _analysis(), MasteringPolicy()
        )
