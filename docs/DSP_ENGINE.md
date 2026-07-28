# DSP engine (v3.3)

## Processor contract

Each processor accepts normalized float64 samples with shape `(frames, channels)` and a
positive sample rate, returns a new buffer with the same shape, and has no hidden
mutable state. `DspPipeline` applies processors in declared order.

## Available processors

- `HighPassProcessor`: optional fourth-order infrasonic filtering.
- `TonalEqualizerProcessor`: fixed 100 Hz, 1 kHz, and 10 kHz peaking bands.
- `DynamicEqualizerProcessor`, `BassControlProcessor`, and `DeEsserProcessor`:
  independently linked, frequency-selective reduction.
- `GainProcessor`: fixed dB gain staging.
- `SaturationProcessor` and `OversampledClipperProcessor`: optional bounded nonlinear
  stages.
- `LimiterProcessor`: linked, oversampled peak detection with configurable lookahead,
  release, and output ceiling.

## Automatic mastering workflow

`AutomaticMasteringService` applies a serialized `MasteringPolicy` to analysis results,
derives an initial gain decision bounded by `maximum_gain_adjustment_db`, renders the
complete chain, and can atomically export the result as PCM WAV. Positive gain is not
blocked by the source sample peak: the clipper and limiter remain responsible for peak
safety.

EQ, selective dynamics, clipping, and limiter release can make the first render miss
the requested programme loudness. The service therefore measures post-limiter LUFS and
may attempt at most two deterministic correction renders. Total calibration stays
within one decibel of the initial decision as well as the configured gain bound. A
candidate is retained only when its measured target error is smaller; the second
correction uses the observed LU-per-dB response and each individual step is limited to
3 dB. Processing stops within 0.2 LU or when the quality budget is exhausted. The
result records accepted `loudness_correction_passes` and
`target_loudness_error_lu`; an unattainable target remains explicitly visible rather
than driving the limiter indefinitely.

The decision record includes its full policy, effective settings, processor trace, and
headroom evidence so an identical input and policy reproduce the same output.

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

## Limiter and source limitations

The limiter oversamples four times for linked peak detection, applies lookahead and
release smoothing, and checks the reconstructed output against the configured ceiling.
It is deterministic, but no processor can recover transient samples already clipped in
the uploaded source. Very loud targets can also require audible gain reduction; when
quality matters more than numerical loudness, use a premaster with headroom and select
a less aggressive target.
