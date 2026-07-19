# Reference validation

## Scope

OpenMaster cross-validates its deterministic metrics against independent local
implementations where one is available. This is evidence of regression resistance; it
is not a claim of EBU, ITU, or broadcast-compliance certification.

## FFmpeg cross-validation

The test suite generates five-second, 48 kHz, 1 kHz sine WAV signals in mono and
dual-mono stereo. It compares OpenMaster integrated loudness and four-times true peak
with the final summary emitted by `ffmpeg`'s `ebur128=peak=true` filter.

Accepted tolerances are 0.35 LUFS and 0.35 dBTP. The tolerance accounts for filter
implementation and display rounding differences while remaining tight enough to catch
channel-energy and oversampling regressions.

Run the cross-validation with:

```bash
python -m pytest tests/test_service.py -k cross_validate
```

FFmpeg is required; the test is skipped in environments that do not provide it.

## Tempo and key

Controlled synthetic click tracks validate 60–200 BPM, including half-tempo ambiguity.
Controlled tonal signals validate the estimator's deterministic behavior. They do not
represent a licensed, annotated music corpus, so v0.7 does not claim real-world key or
tempo accuracy.

## Final-release boundary

An approved external corpus with its licence, expected values, tool versions, and
recorded tolerances is still required before OpenMaster can make compliance or
real-music accuracy claims.
