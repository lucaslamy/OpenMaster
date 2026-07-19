# Analysis engine (v0.7)

## Architecture

`AnalysisService` is the application-facing coordinator. It delegates decoding to
`wav_reader` and independent numerical measurements to `metrics`, then returns the
immutable `AnalysisResult` model. This keeps worker and future API code free of DSP
logic and makes every calculation directly unit-testable.

## Measurements

Levels are expressed in dBFS except integrated loudness (LUFS). True peak uses 4x
polyphase oversampling. Dynamic range is the 95th–10th percentile of 400 ms,
75%-overlapped RMS windows. Stereo width is the side/mid RMS ratio; it is unavailable
for mono. Phase correlation is the left/right Pearson coefficient.

BPM is derived from spectral-flux autocorrelation in the 60–200 BPM range. Key uses
pitch-class energy matched to Krumhansl major/minor profiles. Both may be unavailable
when a clip is too short or has insufficient musical content.

## Input safety and limits

The decoder accepts regular local PCM WAV files only and caps an input at 120 million
sample values before allocation. Invalid input raises a typed analysis exception; it
is never silently interpreted as audio. The API layer should map these exceptions to
client-safe HTTP responses.

## Verification

The regression suite synthesizes stereo, mono-silence, and 24-bit PCM WAV fixtures.
It verifies level accuracy, metadata extraction, unavailable measurements for silence,
and the typed failure modes for missing or unsupported files.
