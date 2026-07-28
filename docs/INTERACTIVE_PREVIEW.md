# Interactive mastering preview

The source uploads once and runs Celery analysis before any master is created. The
browser then streams that immutable original through one Web Audio graph; moving a
supported control never calls Celery or RunPod.

The graph uses three peaking `BiquadFilterNode` bands with the same center frequencies
and Q values as the Python equalizer, a high-pass filter, and `GainNode`. Changes use
`setTargetAtTime`. The persistent transport switches explicitly between **Original**
and **Live effects preview** on the same media element, preserving its clock and
position while settings scroll.

Low, mid, and high EQ plus high-pass cutoff use native nodes directly. Dynamic EQ, bass
control, and de-essing remain final-render controls: one broadband browser compressor
cannot represent those independent bands and previously made sub-heavy material pump,
so it is deliberately bypassed. An AudioWorklet auditions target-loudness gain,
maximum correction, saturation, soft clipping, lookahead/release limiting, ceiling,
and dithered 16/24/32-bit quantization. Its gain is derived from the analyzed source
LUFS, not the preset that happened to be active when the component mounted. These
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
returns a signed proof whose lifetime defaults to two hours and is configurable from
60 seconds through 24 hours with `MASTERING_ACCESS_TOKEN_TTL_SECONDS`. Upload and
final-render endpoints require that proof, so a bad password returns before audio
transfer and direct calls cannot bypass authorization. The longer default covers slow
multipart transfers because FastAPI validates the proof after parsing the upload.

Source transfer uses browser upload progress events and displays real bytes and
percentages. Once the browser reaches 100%, the interface distinguishes server-side
validation and MinIO storage from the transfer itself. Analysis and mastering remain
indeterminate until their workers publish finer-grained progress. When mastering
transitions to `succeeded`, the page scrolls to the `05 Before / after` comparison for
that same job; opening an older completed project never triggers this behavior.

`Rap Reloaded` is a separate, tested preset and does not replace `Rap`. It targets
−10.5 LUFS with a −1 dBTP ceiling, no clipper or saturation, a six-decibel correction
bound, neutral bass EQ, no bass-band compression, five-millisecond lookahead, and a
70-millisecond release. Its purpose and measured validation are documented in
`docs/RAP_RELOADED.md`.
