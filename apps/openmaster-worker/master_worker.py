"""Worker entry point for the deterministic analysis stage."""

from pathlib import Path

from packages.analysis_engine import AnalysisResult, AnalysisService


def process(path: str | Path) -> AnalysisResult:
    """Analyse one local audio file for a worker caller."""
    return AnalysisService().analyze(path)
