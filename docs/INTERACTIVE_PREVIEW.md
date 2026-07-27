# Interactive mastering preview

The source uploads once and runs Celery analysis before any master is created. The
browser then streams that immutable original through one Web Audio graph; moving a
supported control never calls Celery or RunPod.

The graph uses three `BiquadFilterNode` bands, a high-pass filter,
`DynamicsCompressorNode`, and `GainNode`. Changes use `setTargetAtTime`. The persistent
transport switches explicitly between **Original** and **Live effects preview** on the
same media element, preserving its clock and position while settings scroll.

Low, mid, and high EQ plus high-pass cutoff use native nodes directly. Dynamic EQ, bass
control, and de-essing use the native compressor as an approximation. An AudioWorklet
auditions target-loudness gain, maximum correction, saturation, soft clipping,
lookahead/release limiting, ceiling, and dithered 16/24/32-bit quantization. These
worklet stages are real local DSP but remain approximations of the oversampled Python
renderer. AI assistance still requires a complete render. Canonical metadata lives in
`apps/web/src/masteringParameters.ts`.

Every completed master is an immutable download. Further settings and render requests
continue from the retained source rather than processing a previous master.

Inline source and master preview signatures last two hours. The persistent browser
transport proactively requests a fresh source redirect every twelve minutes, restores
the current position, and resumes playback when browser autoplay policy permits it.
This prevents the former fifteen-minute signed-URL interruption during long sessions.

The preview rail includes a real analyser-driven spectrum. Decorative signal sprites
and all other motion respect the operating system's reduced-motion preference.

Saving settings performs no audio work. An authorized idempotent final-render child job
points to the existing source, copies completed analysis, and dispatches directly to
mastering. The local preview is approximate; the downloadable WAV uses the full engine.

Passwords are never put in URLs or persisted in the browser. A small password-only POST
returns a signed proof valid for 60 seconds. Upload and final-render endpoints require
that proof, so a bad password returns before audio transfer and direct calls cannot
bypass authorization.
