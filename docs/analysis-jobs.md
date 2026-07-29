# Analysis and mastering jobs API

OpenMaster exposes a durable asynchronous API for WAV, AIFF, FLAC, M4A, MP3, OGG,
and Opus analysis and mastering.

## Contract

Create an account request once:

```bash
curl -fsS -c openmaster.cookies \
  -H "Content-Type: application/json" \
  -d '{"display_name":"Studio","email":"studio@example.com","password":"replace-with-a-long-password"}' \
  https://openmaster.example.com/api/v1/auth/register
```

An administrator must approve the request before `/api/v1/auth/login` returns the
secure session cookie. Submit one file with that cookie and a stable idempotency key:

```bash
curl -fsS -X POST \
  -b openmaster.cookies \
  -H "Idempotency-Key: $(uuidgen)" \
  -F "file=@mix.mp3" \
  -F "target_lufs=-14" \
  -F "maximum_gain_adjustment_db=12" \
  -F "ceiling_dbfs=-1" \
  -F "eq_low_gain_db=0" \
  -F "eq_mid_gain_db=0" \
  -F "eq_high_gain_db=0" \
  -F "clipper_drive_db=1" \
  -F "limiter_lookahead_ms=3" \
  -F "limiter_release_ms=80" \
  -F "high_pass_enabled=true" \
  -F "high_pass_cutoff_hz=25" \
  -F "dynamic_eq_reduction_db=2" \
  -F "bass_control_reduction_db=2" \
  -F "de_esser_reduction_db=2" \
  -F "saturation_amount=0.15" \
  -F "ai_assist_enabled=true" \
  -F "bit_depth=24" \
  https://openmaster.example.com/api/v1/analysis-jobs
```

The API validates account ownership, the extension, and configured upload limit, stores the immutable
source under `analysis/<job-id>/source.<ext>` in the private MinIO bucket, persists
the queued job in PostgreSQL, and publishes `openmaster.analysis_object` to the
Celery `analysis` queue. After analysis, the worker publishes a mastering task. The
mastering worker creates the assistant recommendation, renders locally or delegates
the render to RunPod, then publishes the final WAV in MinIO.

The response is HTTP 202:

```json
{"id":"...","status":"queued","result":null,"error_code":null,"error_message":null}
```

Poll the durable state:

```bash
curl -fsS \
  -b openmaster.cookies \
  https://openmaster.example.com/api/v1/analysis-jobs/JOB_ID
```

The normal state sequence is `queued -> running -> mastering -> succeeded`. Terminal
states are `succeeded` and `failed`. A successful response contains the deterministic
analysis in `result`, the explainable assistant output in `recommendation`, the render
audit record in `mastering_result`, compact `source_waveform` and `master_waveform`
envelopes, fixed-scale source/master spectral profiles and RMS level timelines, and
relative `preview_url` and `download_url` values. Preview redirects
inline for the A/B audio player; download adds a signed attachment filename while both
keep the MinIO object private.

The exported name is stable across retries and follows:

```text
<original-stem>-<bit-depth>bit-openmaster-<UTC timestamp>.wav
```

For example, `My mix.wav` created at 12:34:56 UTC becomes
`My-mix-24bit-openmaster-20260725T123456Z.wav`.

Download the final WAV:

```bash
curl -fL \
  -b openmaster.cookies \
  https://openmaster.example.com/api/v1/analysis-jobs/JOB_ID/download \
  -o master.wav
```

A failed job contains a bounded public error and keeps technical details in worker logs.

Repeated POST requests with the same `Idempotency-Key` return the same job and never
upload a second object. A queued job may be dispatched again safely if the original
broker publication was interrupted.

## Operational requirements

- Alembic revision `0012` must be applied.
- API and analysis-worker images must contain FFmpeg and `python-multipart`.
- `DATABASE_URL`, Celery URLs, and MinIO credentials must be present in the runtime
  Secret.
- `AUTH_SESSION_DAYS` controls the bounded database session lifetime. Production keeps
  `AUTH_COOKIE_SECURE=true`; local plain-HTTP development may set it to `false`.
- `OPENMASTER_ADMIN_EMAIL` and `OPENMASTER_ADMIN_PASSWORD` must be supplied by the
  runtime Secret before the API starts.
- `MASTERING_ACCESS_PASSWORD` remains in the runtime Secret only for the deprecated
  `/mastering-access` compatibility endpoint; browser uploads use the account session.
- `MINIO_INTERNAL_ENDPOINT`, `MINIO_PUBLIC_ENDPOINT`, `MINIO_BUCKET`, and
  `MINIO_REGION` are rendered by Helm. The public endpoint must be reachable by the
  user's browser for signed downloads.
- The API and analysis worker need NetworkPolicy access to PostgreSQL, Redis, and MinIO.
- The mastering worker needs access to PostgreSQL and MinIO; with RunPod enabled it also
  needs the configured remote HTTPS egress.
- `/tmp` must remain writable because multipart uploads and FFmpeg use bounded
  ephemeral storage.
- ingress-nginx must allow a request body at least as large as `MAX_UPLOAD_BYTES`.

Audio objects are intentionally not placed in PostgreSQL or application logs.

## Mastering controls

The upload contract exposes only settings implemented by the deterministic engine:

| Field | Allowed range | Default | Effect |
| --- | --- | --- | --- |
| `target_lufs` | -24 to -8 | -14 | Requested integrated-loudness target |
| `maximum_gain_adjustment_db` | 0 to 12 | 12 | Bounds positive and negative gain correction |
| `ceiling_dbfs` | -6 to -0.1 | -1 | Linked True Peak limiter ceiling |
| `eq_low_gain_db` | -6 to 6 | 0 | 100 Hz tonal correction |
| `eq_mid_gain_db` | -6 to 6 | 0 | 1 kHz tonal correction |
| `eq_high_gain_db` | -6 to 6 | 0 | 10 kHz tonal correction |
| `clipper_drive_db` | 0 to 12 | 0 | Drive into the 4x oversampled soft clipper |
| `limiter_lookahead_ms` | 0 to 10 | 3 | Peak anticipation horizon |
| `limiter_release_ms` | 10 to 500 | 80 | Gain-recovery time after limiting |
| `high_pass_enabled` | boolean | true | Enables the subsonic high-pass |
| `high_pass_cutoff_hz` | 15 to 80 | 25 | Subsonic high-pass cutoff |
| `dynamic_eq_reduction_db` | 0 to 12 | 0 | Maximum attenuation near 2.5 kHz |
| `bass_control_reduction_db` | 0 to 12 | 0 | Maximum linked attenuation below 140 Hz |
| `de_esser_reduction_db` | 0 to 12 | 0 | Maximum attenuation near 7 kHz |
| `saturation_amount` | 0 to 1 | 0 | Oversampled light-saturation blend |
| `ai_assist_enabled` | boolean | false | Ask the private LamAI gateway for bounded settings |
| `bit_depth` | 16, 24, or 32 | 24 | Final PCM WAV depth |

These values are persisted with the job and sent unchanged to local or RunPod
mastering. The assistant can still reduce effective gain when measured peak headroom
requires it.

The deterministic render order is subsonic high-pass, three-band tonal EQ, dynamic
EQ, linked bass control, de-esser, gain staging, oversampled light saturation,
four-times oversampled soft clipping, and a linked four-times oversampled True Peak
limiter. OpenMaster then measures integrated LUFS and reconstructed True Peak on the
rendered signal. Integer PCM export applies deterministic TPDF dither as its final
stage. A zero reduction or zero saturation amount is an explicit bypass.

The web safeguard switches are shortcuts over these same fields: extra headroom lowers
the ceiling, gentle correction narrows the gain bound, and high resolution selects
24-bit output. They do not enable undisclosed processors.

## Expected 404 response

`GET /api/v1/analysis-jobs/inexistant` intentionally returns HTTP 404 because that job
does not exist. `curl -f` converts any 4xx response to exit code 22 and can hide the
response body. Inspect the API error with:

```bash
curl -sk https://openmaster.example.com/api/v1/analysis-jobs/inexistant
```

The expected body is `{"detail":"Analysis job not found"}`.

## Current web scope

The single-file web path exposes upload, analysis, assistant recommendation, automatic
mastering, six measurement views, contextual control documentation, WAV export,
download, synchronized A/B playback, and a draggable source/master waveform comparison.
Waveforms are compact peak envelopes relative to digital full scale for visual
comparison, not loudness meters. The web sliders interpolate the stored original and
master values point by point. Completed jobs also include an averaged log-frequency
profile on a fixed −100..0 dBFS scale and a windowed RMS timeline on a fixed
−60..0 dBFS scale. The latter is not labelled LUFS because it does not apply the
complete integrated-loudness gating contract.
Reference matching, aligned multi-stem sessions, and third-party plugin configuration
have distinct multi-file or privileged execution contracts and are not yet exposed by
this endpoint.
