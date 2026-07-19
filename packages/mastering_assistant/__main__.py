"""Command-line entry point for explainable mastering recommendations."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from packages.analysis_engine import AnalysisService
from packages.audio_core import AudioInputError, decode_audio

from .service import MasteringAssistant


def main(argv: Sequence[str] | None = None) -> int:
    """Analyse one local audio file and print an auditable recommendation as JSON."""
    parser = argparse.ArgumentParser(
        description="Recommend deterministic OpenMaster mastering settings."
    )
    parser.add_argument("input_path", help="Path to a supported local input audio file")
    parser.add_argument("--target-lufs", type=float, default=-14.0)
    parser.add_argument("--maximum-gain-adjustment-db", type=float, default=12.0)
    parser.add_argument("--ceiling-dbfs", type=float, default=-1.0)
    arguments = parser.parse_args(argv)

    try:
        decoded = decode_audio(arguments.input_path)
        analysis = AnalysisService().analyze_decoded(decoded)
        recommendation = MasteringAssistant().recommend(
            analysis,
            target_lufs=arguments.target_lufs,
            maximum_gain_adjustment_db=arguments.maximum_gain_adjustment_db,
            ceiling_dbfs=arguments.ceiling_dbfs,
        )
    except (AudioInputError, ValueError) as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 2

    print(
        json.dumps(
            {"analysis": analysis.to_dict(), "recommendation": recommendation.to_dict()},
            allow_nan=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
