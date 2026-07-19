"""Reference isolated plugin implementing explicit fixed gain for integration tests."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

import numpy as np

from packages.dsp_engine import GainProcessor


def main(argv: Sequence[str] | None = None) -> int:
    """Apply the configured gain using the isolated plugin file protocol."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--config", required=True)
    parser.add_argument("--sample-rate", required=True, type=int)
    arguments = parser.parse_args(argv)
    configuration = json.loads(Path(arguments.config).read_text(encoding="utf-8"))
    gain_db = configuration.get("gain_db")
    if not isinstance(gain_db, (int, float)):
        raise ValueError("Reference gain plugin requires a numeric gain_db")
    samples = np.asarray(np.load(arguments.input, allow_pickle=False), dtype=np.float64)
    np.save(arguments.output, GainProcessor(float(gain_db)).process(samples, arguments.sample_rate))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
