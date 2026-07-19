# OpenMaster v0.7.0-alpha.1

OpenMaster is an open-source professional audio mastering platform. This first v0.7
increment replaces the analysis scaffold with a deterministic CPU analysis engine.

## Current capability

`AnalysisService` accepts integer PCM WAV files (8/16/24/32 bit) and returns typed
metadata plus duration, sample rate, bit depth, channels, LUFS, RMS, sample and true
peak, dynamic range, crest factor, BPM, key, stereo width, phase correlation, and
spectral centroid. The analysis is local, deterministic, and has no network or GPU
dependency.

```python
from packages.analysis_engine import AnalysisService

result = AnalysisService().analyze("mix.wav")
print(result.to_dict())
```

## Development

Requires Python 3.12+ and the dependencies declared in `pyproject.toml`.

```bash
python -m pytest
python -m ruff check .
python -m black --check .
python -m mypy packages
```

## Current limits

The built-in decoder intentionally supports PCM WAV only. Production support for
compressed and lossless formats will be added through a validated FFmpeg-based audio
core decoder. Loudness, tempo, and key are deterministic estimates; results should be
validated against a reference corpus before they are used as compliance measurements.
