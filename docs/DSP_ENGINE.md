# DSP engine (v2.0)

## Processor contract

Each processor accepts normalized float64 samples with shape `(frames, channels)` and a
positive sample rate, returns a new buffer with the same shape, and has no hidden
mutable state. `DspPipeline` applies processors in declared order.

## Available processors

- `GainProcessor`: fixed dB gain staging.
- `LimiterProcessor`: linked, instantaneous sample-peak ceiling. One gain is calculated
  per frame from the loudest channel, preserving the stereo relationship.

## Automatic mastering workflow

`AutomaticMasteringService` applies a serialized `MasteringPolicy` to analysis results,
derives a bounded gain decision, constrains it by measured sample-peak headroom, renders
the ordered gain/limiter chain, and can atomically export the result as PCM WAV. The
decision record includes its full policy, effective settings, processor trace, and
headroom constraint so an identical input and policy reproduce the same output.

The v1.1 mastering assistant is advisory only. It produces the same explicit policy
and decision contract with confidence and findings; it does not bypass this workflow
or introduce hidden processor settings.

The v1.2 reference matcher derives a loudness target only within its configured safe
range, and preserves the assistant's gain bound. Its spectral and stereo comparisons
are review findings, not unimplemented hidden DSP operations.

## v2.0 execution extensions

Stem-group mastering applies one static gain and one per-frame limiter envelope across
all aligned stems, so their rendered sum stays protected without independent stem
limiter balance shifts. The CPU NumPy implementation is canonical; CuPy acceleration is
optional and explicit. External plugins run in a separate process over an NPY/JSON
protocol and have their output shape and finite values validated by the host.

## Limiter limitation

The current limiter has no lookahead, release, or true-peak oversampling. It is a
deterministic sample-peak safety processor, not yet a transparent mastering maximizer.
Those controls require their own validated processor implementation.
