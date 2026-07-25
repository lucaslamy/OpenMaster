# Analysis and mastering jobs API

OpenMaster exposes a durable asynchronous API for WAV, AIFF, FLAC, M4A, MP3, OGG,
and Opus analysis and mastering.

## Contract

Submit one file with a stable idempotency key:

```bash
curl -fsS -X POST \
  -H "Idempotency-Key: $(uuidgen)" \
  -F "file=@mix.mp3" \
  -F "target_lufs=-14" \
  -F "maximum_gain_adjustment_db=12" \
  -F "ceiling_dbfs=-1" \
  -F "bit_depth=24" \
  https://openmaster.example.com/api/v1/analysis-jobs
```

The API validates the extension and configured upload limit, stores the immutable
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
  https://openmaster.example.com/api/v1/analysis-jobs/JOB_ID
```

The normal state sequence is `queued -> running -> mastering -> succeeded`. Terminal
states are `succeeded` and `failed`. A successful response contains the deterministic
analysis in `result`, the explainable assistant output in `recommendation`, the render
audit record in `mastering_result`, compact `source_waveform` and `master_waveform`
envelopes, and relative `preview_url` and `download_url` values. Preview redirects
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
  https://openmaster.example.com/api/v1/analysis-jobs/JOB_ID/download \
  -o master.wav
```

A failed job contains a bounded public error and keeps technical details in worker logs.

Repeated POST requests with the same `Idempotency-Key` return the same job and never
upload a second object. A queued job may be dispatched again safely if the original
broker publication was interrupted.

## Operational requirements

- Alembic revision `0005` must be applied.
- API and analysis-worker images must contain FFmpeg and `python-multipart`.
- `DATABASE_URL`, Celery URLs, and MinIO credentials must be present in the runtime
  Secret.
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
| `ceiling_dbfs` | -6 to -0.1 | -1 | Linked sample-peak limiter ceiling |
| `bit_depth` | 16, 24, or 32 | 24 | Final PCM WAV depth |

These values are persisted with the job and sent unchanged to local or RunPod
mastering. The assistant can still reduce effective gain when measured peak headroom
requires it.

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
Waveforms are normalized compact peak envelopes for visual navigation, not loudness
meters. The spectral view places the measured centroid on a logarithmic audible axis;
it deliberately does not invent a full spectrum that the aggregate API does not return.
Reference matching, aligned multi-stem sessions, and third-party plugin configuration
have distinct multi-file or privileged execution contracts and are not yet exposed by
this endpoint.
