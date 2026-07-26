# Interactive mastering preview

The first master still uploads once, runs Celery analysis, and renders through the
selected local or RunPod engine. The browser then streams that immutable master through
one Web Audio graph; moving a supported control never calls Celery or RunPod.

The graph uses three `BiquadFilterNode` bands, a high-pass filter,
`DynamicsCompressorNode`, and `GainNode`. Changes use `setTargetAtTime`. A/B bypasses
the nodes on the same media element, preserving its clock and position.

Low, mid, and high EQ plus high-pass cutoff use native nodes directly. Dynamic EQ, bass
control, and de-essing use the native compressor as an approximation. An AudioWorklet
auditions target-loudness gain, maximum correction, saturation, soft clipping,
lookahead/release limiting, ceiling, and dithered 16/24/32-bit quantization. These
worklet stages are real local DSP but remain approximations of the oversampled Python
renderer. AI assistance still requires a complete render. Canonical metadata lives in
`apps/web/src/masteringParameters.ts`.

Saving settings performs no audio work. An authorized idempotent final-render child job
points to the existing source, copies completed analysis, and dispatches directly to
mastering. The local preview is approximate; the downloadable WAV uses the full engine.

Passwords are never put in URLs or persisted in the browser. A small password-only POST
returns a signed proof valid for 60 seconds. Upload and final-render endpoints require
that proof, so a bad password returns before audio transfer and direct calls cannot
bypass authorization.
