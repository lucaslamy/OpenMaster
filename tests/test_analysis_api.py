"""Route registration tests for the analysis HTTP contract."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from apps.api.analysis_routes import (
    DEFAULT_MASTERING_TOKEN_TTL_SECONDS,
    MASTERING_TOKEN_TTL_ENV,
    create_mastering_token,
    verify_mastering_access,
    verify_mastering_token,
)
from apps.api.main import app


def test_api_registers_analysis_routes_under_ingress_prefix() -> None:
    paths = {route.path for route in app.routes}

    assert "/api/v1/analysis-jobs" in paths
    assert "/api/v1/mastering-access" in paths
    assert "/api/v1/analysis-jobs/{job_id}" in paths
    assert "/api/v1/analysis-jobs/{job_id}/download" in paths
    assert "/api/v1/analysis-jobs/{job_id}/preview" in paths
    assert "/api/v1/analysis-jobs/{job_id}/source" in paths
    assert "/api/v1/analysis-jobs/{job_id}/master" in paths


def test_mastering_password_is_required_and_compared_safely(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MASTERING_ACCESS_PASSWORD", "correct horse battery staple")

    verify_mastering_access("correct horse battery staple")
    with pytest.raises(HTTPException) as invalid:
        verify_mastering_access("wrong")
    assert invalid.value.status_code == 401


def test_missing_mastering_password_configuration_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("MASTERING_ACCESS_PASSWORD", raising=False)

    with pytest.raises(HTTPException) as missing:
        verify_mastering_access("anything")
    assert missing.value.status_code == 503


def test_short_lived_mastering_token_cannot_be_forged_or_used_after_expiry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MASTERING_ACCESS_PASSWORD", "correct horse battery staple")
    monkeypatch.setenv(MASTERING_TOKEN_TTL_ENV, "60")
    monkeypatch.setattr("apps.api.analysis_routes.time.time", lambda: 1_000)
    authorization = create_mastering_token("correct horse battery staple")

    verify_mastering_token(authorization.token)
    with pytest.raises(HTTPException) as forged:
        verify_mastering_token(f"{authorization.token}changed")
    assert forged.value.status_code == 401

    monkeypatch.setattr("apps.api.analysis_routes.time.time", lambda: 1_061)
    with pytest.raises(HTTPException) as expired:
        verify_mastering_token(authorization.token)
    assert expired.value.status_code == 401


def test_mastering_token_uses_upload_safe_default_lifetime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MASTERING_ACCESS_PASSWORD", "correct horse battery staple")
    monkeypatch.delenv(MASTERING_TOKEN_TTL_ENV, raising=False)
    monkeypatch.setattr("apps.api.analysis_routes.time.time", lambda: 1_000)

    authorization = create_mastering_token("correct horse battery staple")

    assert authorization.expires_in_seconds == DEFAULT_MASTERING_TOKEN_TTL_SECONDS
    assert int(authorization.token.split(".", 1)[0]) == (
        1_000 + DEFAULT_MASTERING_TOKEN_TTL_SECONDS
    )


def test_mastering_token_accepts_a_bounded_custom_lifetime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MASTERING_ACCESS_PASSWORD", "correct horse battery staple")
    monkeypatch.setenv(MASTERING_TOKEN_TTL_ENV, "1800")
    monkeypatch.setattr("apps.api.analysis_routes.time.time", lambda: 1_000)

    authorization = create_mastering_token("correct horse battery staple")

    assert authorization.expires_in_seconds == 1_800
    assert int(authorization.token.split(".", 1)[0]) == 2_800


@pytest.mark.parametrize("configured_lifetime", ["", "invalid", "59", "86401"])
def test_mastering_token_rejects_an_unsafe_configured_lifetime(
    monkeypatch: pytest.MonkeyPatch,
    configured_lifetime: str,
) -> None:
    monkeypatch.setenv("MASTERING_ACCESS_PASSWORD", "correct horse battery staple")
    monkeypatch.setenv(MASTERING_TOKEN_TTL_ENV, configured_lifetime)

    with pytest.raises(HTTPException) as invalid:
        create_mastering_token("correct horse battery staple")

    assert invalid.value.status_code == 503
    assert invalid.value.detail == "Mastering authorization token lifetime is misconfigured"
