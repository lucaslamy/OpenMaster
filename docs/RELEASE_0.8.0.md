# OpenMaster 0.8.0

## Release scope

OpenMaster 0.8.0 releases the first stable deterministic DSP foundation. It builds on
the v0.7 local analysis engine and is intended for composable, reproducible processing
in local integrations.

## Included

- Typed `DspProcessor` contract with explicit sample-rate input.
- Immutable ordered `DspPipeline` and named automatic-mastering composition root.
- Fixed dB `GainProcessor`.
- Linked `LimiterProcessor` with a configurable sample-peak ceiling.
- Unit coverage for ordering, immutability, ceiling enforcement, and stereo linking.

## Verification

```bash
python -m ruff check .
python -m black --check .
python -m mypy packages
python -m pytest
```

## Explicit non-goals

This release does not yet include parametric EQ, compression, stereo imaging,
saturation, export, or a lookahead/true-peak mastering limiter. The included limiter
is an instantaneous sample-peak safety processor and may introduce distortion on fast
transients; it is not a transparent maximizer.
