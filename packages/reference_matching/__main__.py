"""Command-line entry point for explainable reference matching."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence

from packages.analysis_engine import AnalysisService
from packages.audio_core import AudioInputError, decode_audio

from .service import ReferenceMatchingService, ReferenceMatchPolicy


def main(argv: Sequence[str] | None = None) -> int:
    """Compare a local input and reference, then print bounded advice as JSON."""
    parser = argparse.ArgumentParser(
        description="Compare audio against a reference with deterministic OpenMaster advice."
    )
    parser.add_argument("input_path", help="Path to the mix being mastered")
    parser.add_argument("reference_path", help="Path to the selected reference audio")
    parser.add_argument("--minimum-target-lufs", type=float, default=-20.0)
    parser.add_argument("--maximum-target-lufs", type=float, default=-8.0)
    parser.add_argument("--maximum-gain-adjustment-db", type=float, default=6.0)
    parser.add_argument("--ceiling-dbfs", type=float, default=-1.0)
    arguments = parser.parse_args(argv)

    try:
        input_audio = decode_audio(arguments.input_path)
        reference_audio = decode_audio(arguments.reference_path)
        analysis_service = AnalysisService()
        input_analysis = analysis_service.analyze_decoded(input_audio)
        reference_analysis = analysis_service.analyze_decoded(reference_audio)
        recommendation = ReferenceMatchingService().match(
            input_analysis,
            reference_analysis,
            ReferenceMatchPolicy(
                minimum_target_lufs=arguments.minimum_target_lufs,
                maximum_target_lufs=arguments.maximum_target_lufs,
                maximum_gain_adjustment_db=arguments.maximum_gain_adjustment_db,
                ceiling_dbfs=arguments.ceiling_dbfs,
            ),
        )
    except (AudioInputError, ValueError) as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 2

    print(
        json.dumps(
            {
                "input_analysis": input_analysis.to_dict(),
                "reference_analysis": reference_analysis.to_dict(),
                "recommendation": recommendation.to_dict(),
            },
            allow_nan=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
