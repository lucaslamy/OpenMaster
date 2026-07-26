"""Narrow, server-side LamAI client with strict mastering-policy validation."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from packages.analysis_engine import AnalysisResult
from packages.dsp_engine import MasteringPolicy


class LamAiMasteringError(RuntimeError):
    """Raised when LamAI cannot provide safe, parseable mastering advice."""


@dataclass(frozen=True, slots=True)
class AiMasteringAdvice:
    """Validated policy and human-readable rationale returned by LamAI."""

    policy: MasteringPolicy
    rationale: str
    model: str


class LamAiMasteringClient:
    """Ask LamAI for bounded settings without sending audio or storage URLs."""

    def __init__(self, base_url: str, api_key: str, *, timeout_seconds: float = 90.0) -> None:
        if not base_url.startswith(("http://", "https://")):
            raise ValueError("LamAI base URL must use HTTP or HTTPS")
        if not api_key:
            raise ValueError("LamAI API key is required")
        self._url = f"{base_url.rstrip('/')}/v1/chat"
        self._api_key = api_key
        self._timeout = timeout_seconds

    @classmethod
    def from_environment(cls) -> LamAiMasteringClient:
        """Build the client exclusively from server-side environment variables."""
        return cls(
            os.environ["LAMAI_BASE_URL"],
            os.environ["LAMAI_API_KEY"],
            timeout_seconds=float(os.environ.get("LAMAI_TIMEOUT_SECONDS", "90")),
        )

    def recommend(
        self,
        analysis: AnalysisResult,
        current_policy: MasteringPolicy,
    ) -> AiMasteringAdvice:
        """Return a policy only after validating every model-provided value."""
        prompt = _prompt(analysis, current_policy)
        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are OpenMaster's mastering adviser. Return JSON only. "
                        "Never invent measurements and never exceed the stated bounds."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 900,
            "thinking": False,
        }
        request = Request(
            self._url,
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self._timeout) as response:  # noqa: S310
                body = json.loads(response.read())
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
            raise LamAiMasteringError("LamAI request failed") from error
        try:
            model = str(body["model"])
            content = str(body["message"]["content"])
            document = _json_document(content)
            settings = document["settings"]
            rationale = str(document["rationale"]).strip()
            if not isinstance(settings, dict) or not rationale or len(rationale) > 2_000:
                raise ValueError
            policy = MasteringPolicy(**_policy_values(settings))
        except (KeyError, TypeError, ValueError) as error:
            raise LamAiMasteringError("LamAI returned invalid mastering advice") from error
        return AiMasteringAdvice(policy=policy, rationale=rationale, model=model)


def _prompt(analysis: AnalysisResult, policy: MasteringPolicy) -> str:
    """Build a data-minimal prompt containing measurements and current controls."""
    bounds = {
        "target_lufs": [-24, -8],
        "maximum_gain_adjustment_db": [0, 12],
        "ceiling_dbfs": [-6, -0.1],
        "eq_low_gain_db": [-6, 6],
        "eq_mid_gain_db": [-6, 6],
        "eq_high_gain_db": [-6, 6],
        "clipper_drive_db": [0, 12],
        "limiter_lookahead_ms": [0, 10],
        "limiter_release_ms": [10, 500],
        "high_pass_cutoff_hz": [15, 80],
        "dynamic_eq_reduction_db": [0, 12],
        "bass_control_reduction_db": [0, 12],
        "de_esser_reduction_db": [0, 12],
        "saturation_amount": [0, 1],
    }
    return (
        "Choose conservative deterministic mastering settings from these measured facts. "
        "The audio itself is not available. Keep high_pass_enabled boolean. "
        'Return exactly {"settings":{all current setting keys},"rationale":"..."}. '
        f"Measurements: {json.dumps(analysis.to_dict(), allow_nan=False)}. "
        f"Current settings: {json.dumps(asdict(policy), allow_nan=False)}. "
        f"Hard bounds: {json.dumps(bounds)}."
    )


def _json_document(content: str) -> dict[str, Any]:
    """Extract one JSON object while tolerating an accidental Markdown fence."""
    start, end = content.find("{"), content.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("No JSON object")
    document = json.loads(content[start : end + 1])
    if not isinstance(document, dict):
        raise ValueError("Advice must be an object")
    return document


def _policy_values(settings: dict[str, Any]) -> dict[str, Any]:
    """Reject missing and unknown model output before policy construction."""
    allowed = set(asdict(MasteringPolicy()))
    if set(settings) != allowed:
        raise ValueError("Advice settings do not match the policy schema")
    bounds = {
        "target_lufs": (-24.0, -8.0),
        "maximum_gain_adjustment_db": (0.0, 12.0),
        "ceiling_dbfs": (-6.0, -0.1),
        "eq_low_gain_db": (-6.0, 6.0),
        "eq_mid_gain_db": (-6.0, 6.0),
        "eq_high_gain_db": (-6.0, 6.0),
        "clipper_drive_db": (0.0, 12.0),
        "limiter_lookahead_ms": (0.0, 10.0),
        "limiter_release_ms": (10.0, 500.0),
        "high_pass_cutoff_hz": (15.0, 80.0),
        "dynamic_eq_reduction_db": (0.0, 12.0),
        "bass_control_reduction_db": (0.0, 12.0),
        "de_esser_reduction_db": (0.0, 12.0),
        "saturation_amount": (0.0, 1.0),
    }
    for key, (minimum, maximum) in bounds.items():
        value = settings[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{key} must be numeric")
        if not minimum <= float(value) <= maximum:
            raise ValueError(f"{key} is outside safe bounds")
    if not isinstance(settings["high_pass_enabled"], bool):
        raise ValueError("high_pass_enabled must be boolean")
    return {key: settings[key] for key in allowed}
