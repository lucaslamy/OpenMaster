"""Route registration tests for the analysis HTTP contract."""

from __future__ import annotations

from apps.api.main import app


def test_api_registers_analysis_routes_under_ingress_prefix() -> None:
    paths = {route.path for route in app.routes}

    assert "/api/v1/analysis-jobs" in paths
    assert "/api/v1/analysis-jobs/{job_id}" in paths
    assert "/api/v1/analysis-jobs/{job_id}/download" in paths
