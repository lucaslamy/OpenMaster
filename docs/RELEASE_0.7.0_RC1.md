# OpenMaster 0.7.0-rc.1

## Purpose

This release candidate delivers the first usable OpenMaster analysis engine. It is
intended for local evaluation, integration testing, and creation of the validation
corpus required for the final v0.7 release.

## Included

- Typed deterministic analysis results and expected-error model.
- PCM and IEEE-float WAV decoding.
- FFmpeg/FFprobe decoding for AIFF, FLAC, M4A, MP3, OGG, and Opus.
- Programme level, loudness, spectral, stereo, tempo, key, and source measurements.
- JSON command-line interface and installable Python distribution.
- Ruff, Black, MyPy, Pytest, and GitHub Actions quality checks.

## Installation

```bash
python -m pip install "openmaster==0.7.0rc1"
```

For a source checkout, use `python -m pip install -e ".[dev]"`.

## Verification

The release candidate is accepted only when the following commands pass:

```bash
python -m ruff check .
python -m black --check .
python -m mypy packages
python -m pytest
```

## Known limitations

- Audio is fully decoded in memory; long-file streaming is not implemented.
- Loudness, true peak, tempo, and key are estimates pending reference-corpus accuracy
  validation. Do not use them for compliance claims.
- API, persistent job state, worker retries, storage, and observability are still
  required for the final v0.7 service delivery.
- FFmpeg and FFprobe are required for formats other than WAV.

## Path to 0.7.0

The final release requires the v0.7 exit criteria in `ROADMAP.md`: measurement
validation against a reference corpus, a bounded long-audio strategy, extraction of
the reusable audio core, and observable retry-safe API/worker jobs.
