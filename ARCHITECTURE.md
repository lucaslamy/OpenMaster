# OpenMaster architecture

This document describes the current architecture and the intended dependency direction.
It distinguishes implemented components from planned ones.

## Current system

```text
CLI / worker entry point
          |
          v
AnalysisService
   |                  |
   v                  v
WAV decoder       FFmpeg decoder
   |                  |
   +--------> normalized float64 samples
                         |
                         v
                    pure metrics
                         |
                         v
                  AnalysisResult / JSON
```

The implemented analysis package is local and deterministic. It accepts a filesystem
path, validates it, decodes one audio stream, calculates independent measurements, and
returns an immutable `AnalysisResult`. It has no network, database, or API dependency.

## Package boundaries

| Component | Responsibility | Current state |
| --- | --- | --- |
| `packages/analysis_engine` | Decode orchestration and deterministic measurements | Implemented |
| `packages/dsp_engine` | Deterministic processors and auditable automatic-mastering workflow | v1.0 implemented |
| `packages/mastering_assistant` | Explainable, deterministic recommendation and confidence layer | v1.1 implemented |
| `packages/reference_matching` | Bounded reference comparison and recommendation layer | v1.2 implemented |
| `packages/stem_mastering` | Balance-preserving aligned stem-group mastering | v2.0 implemented |
| `packages/compute_backends` | Explicit CPU reference and optional GPU group-limiter backends | v2.0 implemented |
| `packages/plugin_system` | Timeout-bounded isolated external DSP plugin execution | v2.0 implemented |
| `apps/openmaster-worker` | Invoke analysis from a worker caller | Minimal adapter |
| `apps/web` | Vue frontend for upload, mastering controls, progress, audit results, and download | Implemented single-file workflow |
| `apps/api` | FastAPI upload, job polling, signed download, and Kubernetes health boundary | Implemented |
| `packages/audio_core` | Reusable audio contracts, input safety, WAV and FFmpeg decoding | Implemented |
| `packages/job_store` | Pure retry-safe analysis-job lifecycle contracts | Initial extraction |
| `packages/analysis_jobs` | Idempotent upload and asynchronous dispatch service | Implemented |
| `packages/database` | Alembic metadata and durable analysis-job repository | Implemented |
| `packages/storage` | Internal MinIO transfers and public signed URLs | Implemented |
| Auth, AI | Future platform concerns | Planned |

Applications may depend on packages. Packages must not depend on applications. FastAPI
routes must call services; DSP and analysis logic must remain in packages.

## Deployment foundation

The `helm/openmaster` chart owns non-sensitive configuration and references one existing
Kubernetes Secret managed by Vault/External Secrets. It never renders secret values.
It deploys the API, web server, isolated workers, selectable internal or external data
services, a serialized Alembic hook, ingress, least-privilege NetworkPolicies, HPA, and
PDB resources. Atomic deploy, rollback, preflight, and smoke-test scripts provide the
operational boundary for k3s and upstream Kubernetes.
Dedicated Celery deployments consume the `analysis`, `mastering`, and `export` queues;
their commands and resource profiles are rendered from chart values.

## Automatic mastering baseline

`AutomaticMasteringService` consumes an immutable `AnalysisResult`, derives a bounded
gain decision from integrated loudness and measured sample-peak headroom, then delegates
rendering to the deterministic DSP chain. Its result contains both the audio render
trace and the serialized policy plus requested, peak-limited, and effective gain values. The current policy
targets -14 LUFS, limits a correction to 12 dB, and protects the output with a -1 dBFS
linked sample-peak ceiling.

This is deliberately a narrow, deterministic policy rather than an opaque AI model.
The ceiling is a sample-peak guard, not a true-peak compliance guarantee.

## Audio export

`audio_core.encode_wav` writes a normalized float buffer as 16-, 24-, or 32-bit PCM
WAV through an atomic same-directory replacement. It rejects non-finite or out-of-range
samples and protects an existing destination unless replacement is explicitly requested.
`AutomaticMasteringService.master_to_wav` composes this export with the rendered audio
and returns both the output path and the full mastering decision record.

The `python -m packages.dsp_engine` CLI is a local application boundary over that
workflow. It decodes once, passes the decoded stream to analysis, and emits a stable
JSON audit record; expected input, policy, and output failures use JSON stderr with
exit code 2.

## Mastering assistant

`packages/mastering_assistant` is a deterministic advisory layer over immutable
analysis and the v1.0 policy. It returns the exact policy and effective decision it
recommends, a bounded confidence score, and individual findings. It performs no hidden
audio processing and does not require an external model or network connection.

The `python -m packages.mastering_assistant` CLI exposes the same read-only workflow:
decode once, analyse once, then serialize analysis and its recommendation as JSON.
Recommendation documents carry an explicit schema version for integration compatibility.

## Reference matching

`packages/reference_matching` compares immutable input and reference analyses. It clamps
the reference loudness to an explicit safe range, delegates the resulting gain decision
to the v1.1 assistant, and serializes every comparison delta and finding. Spectral and
stereo differences are advisory only: no EQ or imaging is silently introduced.
The `python -m packages.reference_matching` CLI decodes and analyses both inputs once,
then emits the complete versioned comparison document as JSON.

## Stem-group mastering

`packages/stem_mastering` accepts a non-empty, frame-aligned group of decoded stems.
It applies the same static gain and same per-frame group limiter envelope to every stem.
The rendered stems therefore preserve their group balance and sum to the protected group
mix. Misaligned sample rates, frame counts, or channel layouts are rejected.
The `python -m packages.stem_mastering` CLI writes each named output atomically and
returns the full shared decision alongside the output paths as JSON.

## Compute backends

`packages/compute_backends` defines the group-limiter operation used by stem mastering.
NumPy float64 on CPU is the canonical reference. CuPy is an explicitly requested,
optional GPU backend; its absence raises a typed error and never silently changes a
render to another device.

## Isolated plugins

`packages/plugin_system` runs each explicitly configured plugin command in a temporary
subprocess workspace. Audio crosses this boundary as non-pickled NPY buffers and
configuration as finite JSON; output must retain the input shape and finite values.
The host imposes a timeout and never imports third-party plugin code into its process.

## Analysis pipeline

1. Validate a regular local input file and recognized format.
2. Decode PCM/float WAV directly, or probe and decode another supported format through
   FFprobe/FFmpeg.
3. Bound the decoded stream using validated duration and sample-value limits.
4. Compute independent numerical metrics from normalized float64 samples.
5. Return `AnalysisResult`, or raise a typed `AnalysisError` for expected failures.

Consumers that already own a validated `DecodedAudio` can call
`AnalysisService.analyze_decoded` to avoid decoding the same input twice.

The CLI serializes successful results as JSON. Expected analysis errors become JSON on
standard error with exit code 2.

## Technical decisions

### Deterministic DSP remains separate from AI

Analysis and DSP must be reproducible for the same signal and parameters. Future AI
components may recommend settings but must not conceal or mutate processor behavior.

### FFmpeg is an adapter, not business logic

The FFmpeg invocation is contained in `ffmpeg_decoder.py`. Its process output is never
exposed directly to callers; callers receive typed domain errors. `audio_core` already
owns input validation, typed input errors, and resource limits; future extraction can
move this adapter without changing analysis metrics.

### Current limitations

- Analysis currently operates on a fully decoded in-memory signal.
- LUFS, true-peak, tempo, and key estimates require reference-corpus validation before
  compliance claims.
- Authentication and production observability are not implemented.
- Reference matching, aligned stem sessions, and isolated external plugins currently
  remain local typed workflows and are not exposed by the web application.
- The first deployed workflow exports in the mastering task. The dedicated export queue
  remains available for future alternate formats and delivery policies.

## Deployed single-file workflow

```text
Web -> API -> PostgreSQL + MinIO -> Redis -> analysis worker
                                      |
                                      v
                            mastering worker
                         (local CPU or RunPod)
                                      |
                                      v
                  MinIO master -> signed download -> Web
```

The API stores the source in MinIO, persists an idempotent PostgreSQL record, and
dispatches the object key through Celery. The analysis worker persists the deterministic
measurements and chains the mastering task. The mastering worker stores the recommendation,
render audit record, and final object identifier. The web client polls the API and follows
the download endpoint to a short-lived signed MinIO URL.

Analysis now pauses in the durable `analyzed` state. The browser auditions the retained
source with explicitly approximate Web Audio DSP and commits its decision before the API
atomically dispatches mastering. Each master or later render is immutable and reuses
the root source and analysis rather than a previous master. The twenty newest root
projects are exposed as durable history, with editable PostgreSQL display names that
never rename MinIO objects; see `docs/PROJECT_HISTORY.md`.
