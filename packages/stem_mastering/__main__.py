"""Command-line entry point for balance-preserving stem-group mastering."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

from packages.analysis_engine import AnalysisService
from packages.audio_core import AudioInputError, DecodedAudio, decode_audio, encode_wav
from packages.dsp_engine import MasteringPolicy

from .service import StemGroupMasteringService


def main(argv: Sequence[str] | None = None) -> int:
    """Render named, aligned stems with one shared group mastering decision."""
    parser = argparse.ArgumentParser(
        description="Create balance-preserving OpenMaster WAV stems from aligned inputs."
    )
    parser.add_argument("--mix", required=True, help="Mix file used to derive the group decision")
    parser.add_argument(
        "--stem",
        action="append",
        required=True,
        metavar="NAME=PATH",
        help="Named aligned stem; repeat once for each stem",
    )
    parser.add_argument(
        "--output-dir", required=True, help="Existing directory for rendered WAV stems"
    )
    parser.add_argument("--target-lufs", type=float, default=-14.0)
    parser.add_argument("--maximum-gain-adjustment-db", type=float, default=12.0)
    parser.add_argument("--ceiling-dbfs", type=float, default=-1.0)
    parser.add_argument("--bit-depth", type=int, choices=(16, 24, 32), default=24)
    parser.add_argument("--overwrite", action="store_true")
    arguments = parser.parse_args(argv)

    try:
        output_dir = Path(arguments.output_dir)
        if not output_dir.is_dir():
            raise ValueError("Stem output directory does not exist")
        stems = _decode_named_stems(arguments.stem)
        mix_audio = decode_audio(arguments.mix)
        mix_analysis = AnalysisService().analyze_decoded(mix_audio)
        result = StemGroupMasteringService().master(
            stems,
            mix_analysis,
            MasteringPolicy(
                target_lufs=arguments.target_lufs,
                maximum_gain_adjustment_db=arguments.maximum_gain_adjustment_db,
                ceiling_dbfs=arguments.ceiling_dbfs,
            ),
        )
        outputs = []
        for stem in result.stems:
            output_path = encode_wav(
                output_dir / f"{stem.name}.wav",
                stem.samples,
                result.sample_rate_hz,
                bit_depth=arguments.bit_depth,
                overwrite=arguments.overwrite,
            )
            outputs.append(str(output_path))
    except (AudioInputError, OSError, ValueError) as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 2

    print(
        json.dumps(
            {
                "decision": asdict(result.decision),
                "outputs": outputs,
                "processors": result.applied_processors,
            },
            allow_nan=False,
            sort_keys=True,
        )
    )
    return 0


def _decode_named_stems(stem_arguments: Sequence[str]) -> dict[str, DecodedAudio]:
    """Parse safe stem names and decode each stem exactly once."""
    stems: dict[str, DecodedAudio] = {}
    for value in stem_arguments:
        name, separator, path = value.partition("=")
        if not separator or not name or not path or Path(name).name != name:
            raise ValueError("Each stem must use a safe NAME=PATH value")
        if name in stems:
            raise ValueError(f"Duplicate stem name: {name}")
        stems[name] = decode_audio(path)
    return stems


if __name__ == "__main__":
    raise SystemExit(main())
