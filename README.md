# OpenMaster v0.9.0

OpenMaster is an open-source professional audio mastering platform. v0.9 adds the
first stable Vue web-client foundation to the local analysis and DSP packages.

## Current capability

`AnalysisService` accepts PCM WAV (8/16/24/32 bit), IEEE-float WAV (32/64 bit), plus
AIFF, FLAC, M4A, MP3, OGG, and Opus through FFmpeg. It returns typed metadata plus
duration, sample rate, bit depth (when encoded), channels, LUFS, RMS, sample and true
peak, dynamic range, crest factor, BPM, key, stereo width, phase correlation, and
spectral centroid. The analysis is local, deterministic, and has no network or GPU
dependency.

## Web client

The Vue client in `apps/web` submits analysis jobs, polls non-terminal job states, and
renders returned analysis results or errors. It expects the versioned analysis-job API
contract documented in its typed client.

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

The v1.0 work-in-progress automatic mastering flow is also available locally. It
decodes the input once, analyses it, makes a bounded and auditable gain decision, and
writes a protected PCM WAV output:

```bash
python -m packages.dsp_engine mix.wav master.wav --target-lufs -14
```

The command prints the analysis, policy decision, output path, and ordered processor
trace as stable JSON. Existing output files require `--overwrite` explicitly.

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

The Vue client lives in `apps/web` and uses Node.js 22:

```bash
cd apps/web
npm ci
npm run test
npm run build
```

## Current limits

Compressed and lossless formats require the `ffmpeg` and `ffprobe` executables. Their
streams are validated for a known duration, channel count, sample rate, finite samples,
and the analysis allocation limit before measurements run. FFmpeg decoding is also
bounded to the probed stream duration. Loudness, tempo, and key are deterministic
estimates; results should be validated against a reference corpus before they are used
as compliance measurements.
