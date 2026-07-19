"""Subprocess-isolated DSP plugin adapter with strict audio-output validation."""

from __future__ import annotations

import json
import subprocess
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from packages.audio_core import FloatSamples


class PluginExecutionError(RuntimeError):
    """Raised when an isolated plugin cannot safely produce valid audio output."""


@dataclass(frozen=True, slots=True)
class PluginManifest:
    """Explicit identity, command, and resource bound for one external plugin."""

    name: str
    version: str
    command: tuple[str, ...]
    timeout_seconds: float = 30.0

    def __post_init__(self) -> None:
        """Reject ambiguous plugins and unsafe execution configuration."""
        if not self.name or not self.version or not self.command:
            raise ValueError("Plugin name, version, and command are required")
        if self.timeout_seconds <= 0.0:
            raise ValueError("Plugin timeout must be positive")


@dataclass(frozen=True, slots=True)
class IsolatedPluginProcessor:
    """Run a plugin outside the host process using a portable NPY/JSON protocol."""

    manifest: PluginManifest
    configuration: Mapping[str, Any]

    def __post_init__(self) -> None:
        """Ensure configuration is JSON serializable before rendering starts."""
        try:
            json.dumps(self.configuration, allow_nan=False, sort_keys=True)
        except (TypeError, ValueError) as error:
            raise ValueError("Plugin configuration must be finite JSON data") from error

    def process(self, samples: FloatSamples, sample_rate_hz: int) -> FloatSamples:
        """Render a plugin in isolation and accept only finite same-shape float64 output."""
        _validate_input(samples, sample_rate_hz)
        with tempfile.TemporaryDirectory(prefix="openmaster-plugin-") as directory:
            workspace = Path(directory)
            input_path = workspace / "input.npy"
            output_path = workspace / "output.npy"
            configuration_path = workspace / "configuration.json"
            np.save(input_path, samples, allow_pickle=False)
            configuration_path.write_text(
                json.dumps(self.configuration, allow_nan=False, sort_keys=True), encoding="utf-8"
            )
            command = [
                *self.manifest.command,
                "--input",
                str(input_path),
                "--output",
                str(output_path),
                "--config",
                str(configuration_path),
                "--sample-rate",
                str(sample_rate_hz),
            ]
            try:
                completed = subprocess.run(
                    command,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=self.manifest.timeout_seconds,
                )
            except (OSError, subprocess.TimeoutExpired) as error:
                raise PluginExecutionError(
                    f"Plugin '{self.manifest.name}' could not complete safely"
                ) from error
            if completed.returncode != 0:
                raise PluginExecutionError(
                    f"Plugin '{self.manifest.name}' failed with exit code {completed.returncode}"
                )
            try:
                output = np.asarray(np.load(output_path, allow_pickle=False), dtype=np.float64)
            except (OSError, ValueError) as error:
                raise PluginExecutionError(
                    f"Plugin '{self.manifest.name}' did not produce a readable output buffer"
                ) from error
        if output.shape != samples.shape or not np.isfinite(output).all():
            raise PluginExecutionError(
                f"Plugin '{self.manifest.name}' output must be finite with the input shape"
            )
        return output


def _validate_input(samples: FloatSamples, sample_rate_hz: int) -> None:
    """Validate host audio before it crosses the isolated process boundary."""
    if samples.ndim != 2 or samples.shape[0] < 1 or samples.shape[1] < 1:
        raise ValueError("Plugin audio must have shape (frames, channels)")
    if sample_rate_hz < 1 or not np.isfinite(samples).all():
        raise ValueError("Plugin audio and sample rate must be finite and positive")
