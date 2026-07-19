# DSP engine (v0.8)

## Processor contract

Each processor accepts normalized float64 samples with shape `(frames, channels)` and a
positive sample rate, returns a new buffer with the same shape, and has no hidden
mutable state. `DspPipeline` applies processors in declared order.

## Available processors

- `GainProcessor`: fixed dB gain staging.
- `LimiterProcessor`: linked, instantaneous sample-peak ceiling. One gain is calculated
  per frame from the loudest channel, preserving the stereo relationship.

## Limiter limitation

The current limiter has no lookahead, release, or true-peak oversampling. It is a
deterministic sample-peak safety processor, not yet a transparent mastering maximizer.
Those controls require their own validated processor implementation.
