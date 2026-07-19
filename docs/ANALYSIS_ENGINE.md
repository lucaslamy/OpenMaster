# Analysis engine (v0.7)

## Architecture

`AnalysisService` is the application-facing coordinator. It delegates PCM and
IEEE-float WAV decoding to `wav_reader`, other supported formats to the isolated
`ffmpeg_decoder`, and independent numerical measurements to `metrics`, then returns
the immutable `AnalysisResult` model. This keeps worker and future API code free of
DSP logic and makes every calculation directly unit-testable.

Reusable input-path validation, typed input errors, and resource limits live in
`packages.audio_core`. The analysis engine owns orchestration and measurements; this
boundary lets future worker, export, and storage packages apply the same safety policy.

## Measurements

Levels are expressed in dBFS except integrated loudness (LUFS). True peak uses 4x
polyphase oversampling. Integrated loudness sums the energy of mono or stereo channels
before absolute and relative gating. Dynamic range is the 95th–10th percentile of 400 ms,
75%-overlapped RMS windows. Stereo width is the side/mid RMS ratio; it is unavailable
for mono. Phase correlation is the left/right Pearson coefficient.

BPM is derived from spectral-flux autocorrelation in the 60–200 BPM range. Key uses
pitch-class energy matched to Krumhansl major/minor profiles. Both may be unavailable
when a clip is too short or has insufficient musical content.

## Input safety and limits

The decoder accepts regular local PCM WAV files plus AIFF, FLAC, M4A, MP3, OGG, and
Opus when FFmpeg is installed. It caps an input at 120 million sample values before
allocation and bounds FFmpeg decoding to the duration reported by FFprobe. Invalid
input raises a typed analysis exception; it is never silently interpreted as audio. The
API layer should map these exceptions to client-safe HTTP responses.

## Verification

The regression suite synthesizes stereo, mono-silence, and 24-bit PCM WAV fixtures.
It verifies level accuracy, metadata extraction, unavailable measurements for silence,
tempo and key estimation on controlled signals, and typed failure modes for missing or
unsupported files. When FFmpeg is available, it also validates an end-to-end FLAC
decode for AIFF, FLAC, M4A, MP3, OGG, and Opus before signal analysis.

## Command line

Run `python -m packages.analysis_engine path/to/mix.wav` to obtain a JSON analysis
result. This interface maps expected analysis failures to a JSON error on standard
error and exit status 2, which makes it safe to integrate in a worker or shell job.
