# OpenMaster 0.7.0

## Release scope

OpenMaster 0.7.0 is the stable release of the deterministic local analysis engine. It
is suitable for local analysis, command-line integration, and as the package-level
foundation for future workers and applications.

## Included

- Typed analysis result, errors, CLI, and installable Python distribution.
- PCM and IEEE-float WAV support plus FFmpeg/FFprobe adapters for AIFF, FLAC, M4A,
  MP3, OGG, and Opus.
- LUFS, RMS, sample/true peak, dynamic range, crest factor, BPM, key, stereo, phase,
  spectral-centroid, and source metadata measurements.
- `audio_core` decoder, metadata, validation, and resource-limit contracts.
- Regression coverage, FFmpeg loudness/true-peak cross-validation, and quality CI.

## Verification

```bash
python -m ruff check .
python -m black --check .
python -m mypy packages
python -m pytest
```

## Explicit non-goals

This release does not claim loudness compliance certification or real-music tempo/key
accuracy. It does not include persistent API jobs, a distributed worker, object storage,
or long-audio streaming. Those capabilities remain documented post-release work.
