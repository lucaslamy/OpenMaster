"""Command-line entry point for deterministic automatic mastering."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import asdict

from packages.analysis_engine import AnalysisService
from packages.audio_core import AudioInputError, decode_audio

from .automatic import AutomaticMasteringService, MasteringPolicy


def main(argv: Sequence[str] | None = None) -> int:
    """Master one local audio file and serialize its full decision record as JSON."""
    parser = argparse.ArgumentParser(description="Create a deterministic OpenMaster WAV master.")
    parser.add_argument("input_path", help="Path to a supported local input audio file")
    parser.add_argument("output_path", help="Destination .wav or .wave file")
    parser.add_argument("--target-lufs", type=float, default=-14.0)
    parser.add_argument("--maximum-gain-adjustment-db", type=float, default=12.0)
    parser.add_argument("--ceiling-dbfs", type=float, default=-1.0)
    parser.add_argument("--bit-depth", type=int, choices=(16, 24, 32), default=24)
    parser.add_argument("--overwrite", action="store_true")
    arguments = parser.parse_args(argv)

    try:
        decoded = decode_audio(arguments.input_path)
        analysis = AnalysisService().analyze_decoded(decoded)
        service = AutomaticMasteringService(
            MasteringPolicy(
                target_lufs=arguments.target_lufs,
                maximum_gain_adjustment_db=arguments.maximum_gain_adjustment_db,
                ceiling_dbfs=arguments.ceiling_dbfs,
            )
        )
        exported = service.master_to_wav(
            decoded.samples,
            decoded.metadata.sample_rate_hz,
            analysis,
            arguments.output_path,
            bit_depth=arguments.bit_depth,
            overwrite=arguments.overwrite,
        )
    except (AudioInputError, OSError, ValueError) as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 2

    print(
        json.dumps(
            {
                "analysis": analysis.to_dict(),
                "decision": asdict(exported.mastering.decision),
                "output_path": str(exported.output_path),
                "processors": exported.mastering.render.applied_processors,
                "output_lufs": exported.mastering.render.output_lufs,
                "output_true_peak_dbfs": exported.mastering.render.output_true_peak_dbfs,
                "loudness_correction_passes": (exported.mastering.loudness_correction_passes),
                "target_loudness_error_lu": exported.mastering.target_loudness_error_lu,
                "dither_applied": exported.dither_applied,
            },
            allow_nan=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
