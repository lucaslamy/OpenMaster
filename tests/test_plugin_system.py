"""Tests for isolated external DSP plugin execution."""

import sys

import numpy as np
import pytest

from packages.plugin_system import IsolatedPluginProcessor, PluginExecutionError, PluginManifest


def test_isolated_reference_plugin_processes_audio_outside_host_process() -> None:
    processor = IsolatedPluginProcessor(
        PluginManifest(
            name="reference-gain",
            version="1.0",
            command=(sys.executable, "-m", "packages.plugin_system.reference_gain_plugin"),
        ),
        {"gain_db": 6.0206},
    )

    output = processor.process(np.array([[0.25, -0.25]], dtype=np.float64), 48_000)

    assert output == pytest.approx(np.array([[0.5, -0.5]], dtype=np.float64))


def test_isolated_plugin_rejects_non_json_configuration_and_failed_commands() -> None:
    manifest = PluginManifest(name="bad", version="1.0", command=("definitely-not-a-command",))
    with pytest.raises(ValueError, match="JSON"):
        IsolatedPluginProcessor(manifest, {"invalid": object()})
    with pytest.raises(PluginExecutionError, match="could not complete"):
        IsolatedPluginProcessor(manifest, {}).process(np.zeros((1, 1), dtype=np.float64), 48_000)
