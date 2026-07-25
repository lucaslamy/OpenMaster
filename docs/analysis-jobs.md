# Analysis jobs API

OpenMaster exposes a durable asynchronous API for WAV, AIFF, FLAC, M4A, MP3, OGG,
and Opus analysis.

## Contract

Submit one file with a stable idempotency key:

```bash
curl -fsS -X POST \
  -H "Idempotency-Key: $(uuidgen)" \
  -F "file=@mix.mp3" \
  https://openmaster.example.com/api/v1/analysis-jobs
```

The API validates the extension and configured upload limit, stores the immutable
source under `analysis/<job-id>/source.<ext>` in the private MinIO bucket, persists
the queued job in PostgreSQL, and publishes `openmaster.analysis_object` to the
Celery `analysis` queue.

The response is HTTP 202:

```json
{"id":"...","status":"queued","result":null,"error_code":null,"error_message":null}
```

Poll the durable state:

```bash
curl -fsS \
  https://openmaster.example.com/api/v1/analysis-jobs/JOB_ID
```

Terminal states are `succeeded` and `failed`. A successful response contains the
serialized deterministic analysis in `result`. A failed job contains a bounded public
error and keeps technical details in worker logs.

Repeated POST requests with the same `Idempotency-Key` return the same job and never
upload a second object. A queued job may be dispatched again safely if the original
broker publication was interrupted.

## Operational requirements

- Alembic revision `0002` must be applied.
- API and analysis-worker images must contain FFmpeg and `python-multipart`.
- `DATABASE_URL`, Celery URLs, and MinIO credentials must be present in the runtime
  Secret.
- `MINIO_INTERNAL_ENDPOINT`, `MINIO_BUCKET`, and `MINIO_REGION` are rendered by Helm.
- The API and analysis worker need NetworkPolicy access to PostgreSQL, Redis, and MinIO.
- `/tmp` must remain writable because multipart uploads and FFmpeg use bounded
  ephemeral storage.
- ingress-nginx must allow a request body at least as large as `MAX_UPLOAD_BYTES`.

Audio objects are intentionally not placed in PostgreSQL or application logs.
