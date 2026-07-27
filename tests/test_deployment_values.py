"""Tests for the targeted RunPod Helm values updater."""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _module():
    path = Path(__file__).parents[1] / "deployment" / "scripts" / "update-runpod-values.py"
    spec = importlib.util.spec_from_file_location("update_runpod_values", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_update_values_pins_all_cluster_images_and_preserves_runpod_settings(
    tmp_path: Path,
) -> None:
    values = tmp_path / "runpod.yaml"
    values.write_text(
        "remoteCompute:\n  enabled: true\n  endpointId: keep-me\n"
        "image:\n  registry: old\n  tag: old\nweb:\n  replicaCount: 2\n",
        encoding="utf-8",
    )

    _module().update_values(
        values,
        "3.2.0",
        "harbor.lucaslamy.fr/private/openmaster",
    )
    rendered = values.read_text(encoding="utf-8")

    assert 'registry: "harbor.lucaslamy.fr"' in rendered
    assert 'repository: "private/openmaster/api"' in rendered
    assert 'tag: "3.2.0"' in rendered
    assert 'image: "harbor.lucaslamy.fr/private/openmaster/api:3.2.0"' in rendered
    assert 'image: "harbor.lucaslamy.fr/private/openmaster/web:3.2.0"' in rendered
    assert "endpointId: keep-me" in rendered
    assert "replicaCount: 2" in rendered
