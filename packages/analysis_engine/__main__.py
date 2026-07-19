"""Command-line entry point for deterministic OpenMaster audio analysis."""

import argparse
import json
import sys
from collections.abc import Sequence

from .exceptions import AnalysisError
from .service import AnalysisService


def main(argv: Sequence[str] | None = None) -> int:
    """Analyse one local file and print its serialized result to standard output."""
    parser = argparse.ArgumentParser(description="Analyse a PCM WAV file with OpenMaster.")
    parser.add_argument("path", help="Path to the PCM WAV file to analyse")
    arguments = parser.parse_args(argv)

    try:
        result = AnalysisService().analyze(arguments.path)
    except AnalysisError as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 2

    print(json.dumps(result.to_dict(), allow_nan=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
