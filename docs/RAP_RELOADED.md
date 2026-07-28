# Rap Reloaded preset

`Rap Reloaded` is a conservative high-density rap starting point introduced in v3.3.0.
It remains separate from the original `Rap` preset.

## Reference audit

The supplied 24-bit, 44.1 kHz original and OpenMaster render were measured with the
OpenMaster analysis engine, FFmpeg `loudnorm`/`ebur128`, oversampled true-peak
estimation, time-windowed dynamics, stereo M/S energy, spectral bands, and
low-frequency harmonic ratios.

| Measurement | Original | Supplied master | Rap Reloaded validation |
| --- | ---: | ---: | ---: |
| FFmpeg integrated loudness | −12.73 LUFS | −14.46 LUFS | −11.70 LUFS |
| OpenMaster integrated loudness | −11.91 LUFS | −13.84 LUFS | −10.98 LUFS |
| True peak | +0.59 dBTP | −2.17 dBTP | −0.95 dBTP |
| Loudness range | 5.5 LU | 4.4 LU | 3.6–3.7 LU |
| Dynamic range | 13.84 dB | 11.96 dB | 11.56 dB |
| Phase correlation | 0.748 | 0.684 | 0.688 |

The supplied master was therefore about 1.7–1.9 LU quieter while also reducing
dynamics. It left more than one decibel below a −1 dBTP delivery ceiling, shifted the
balance toward the mids, increased low-frequency harmonic energy, and widened the
sub-bass slightly.

The validation render is about 2.75 LU louder than that master and 1.02 LU louder than
the source on FFmpeg's meter. Its linked limiter still makes the already-clipped source
denser, but it keeps the result peak-safe without clipper drive or saturation and shows
no measured sign of newly generated low-frequency harmonics. The source already
contains flattened full-scale samples, so a premaster with headroom remains the only
way to recover more transient contrast.

The supplied render predates the unity-small-signal clipper correction. With the old
curve, even one decibel of drive raised low-level material before the limiter. The
browser preview also used the mounted preset target as its source-loudness baseline
and approximated three selective dynamics stages with one broadband compressor. Both
behaviors disproportionately stressed the 808.

## Settings

| Control | Value |
| --- | ---: |
| Target loudness | −10.5 LUFS |
| Maximum gain correction | 6 dB |
| Limiter ceiling | −1.0 dBTP |
| Low / mid / high EQ | 0 / +0.25 / +0.25 dB |
| High-pass | 20 Hz, enabled |
| Dynamic EQ maximum reduction | 0.5 dB |
| Bass-control maximum reduction | 0 dB |
| De-esser maximum reduction | 0.5 dB |
| Saturation | 0 |
| Clipper drive | 0 dB |
| Limiter lookahead / release | 5 ms / 70 ms |
| WAV export | 24 bit |
| AI assistance | disabled |

The preset avoids nonlinear bass coloration and bass-band compression, keeps the
100 Hz EQ neutral, and uses a 70 ms recovery to avoid holding gain reduction across
successive kicks. The small mid/high lift restores definition without the previous
master's aggressive tonal shift.

It is a starting point, not a promise that every mix will reach exactly −10.5 LUFS.
Post-limiter calibration is deliberately limited to one decibel beyond the initial
loudness decision, and peak protection remains authoritative when a source is already
dense or clipped.
