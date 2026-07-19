# OpenMaster v0.8.0

OpenMaster is an open-source professional audio mastering platform. v0.8 adds the
first stable deterministic DSP foundation to the local analysis engine.

## Current capability

`AnalysisService` accepts PCM WAV (8/16/24/32 bit), IEEE-float WAV (32/64 bit), plus
AIFF, FLAC, M4A, MP3, OGG, and Opus through FFmpeg. It returns typed metadata plus
duration, sample rate, bit depth (when encoded), channels, LUFS, RMS, sample and true
peak, dynamic range, crest factor, BPM, key, stereo width, phase correlation, and
spectral centroid. The analysis is local, deterministic, and has no network or GPU
dependency.

## DSP foundation

`packages.dsp_engine` provides a typed processor contract, ordered deterministic
pipelines, fixed gain staging, and linked sample-peak limiting. See
`docs/DSP_ENGINE.md` for its exact behavior and current limiter limitations.

```python
from packages.analysis_engine import AnalysisService

result = AnalysisService().analyze("mix.wav")
print(result.to_dict())
```

The same analysis is available from the command line:

```bash
python -m packages.analysis_engine mix.wav
```

It prints a stable JSON object to standard output. Invalid or unsupported input is
reported as JSON on standard error and exits with status code 2.

## Development

Requires Python 3.12+ and the dependencies declared in `pyproject.toml`.

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m black --check .
python -m mypy packages
```

The same checks run on every push and pull request in GitHub Actions using Python 3.12.

## Current limits

Compressed and lossless formats require the `ffmpeg` and `ffprobe` executables. Their
streams are validated for a known duration, channel count, sample rate, finite samples,
and the analysis allocation limit before measurements run. FFmpeg decoding is also
bounded to the probed stream duration. Loudness, tempo, and key are deterministic
estimates; results should be validated against a reference corpus before they are used
as compliance measurements.
