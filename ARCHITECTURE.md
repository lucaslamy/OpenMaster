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
| `packages/dsp_engine` | Deterministic processor contracts, pipelines, and gain staging | v0.8 in progress |
| `apps/openmaster-worker` | Invoke analysis from a worker caller | Minimal adapter |
| `apps/web` | Vue frontend and typed analysis-job client | v0.9 in progress |
| `apps/openmaster-api` | HTTP boundary | Scaffold; requires service and persistence refactor |
| `packages/audio_core` | Reusable audio contracts, input safety, WAV and FFmpeg decoding | Implemented |
| `packages/job_store` | Pure retry-safe analysis-job lifecycle contracts | Initial extraction |
| Database, storage, auth, AI | Persistent platform concerns | Planned |

Applications may depend on packages. Packages must not depend on applications. FastAPI
routes must call services; DSP and analysis logic must remain in packages.

## Analysis pipeline

1. Validate a regular local input file and recognized format.
2. Decode PCM/float WAV directly, or probe and decode another supported format through
   FFprobe/FFmpeg.
3. Bound the decoded stream using validated duration and sample-value limits.
4. Compute independent numerical metrics from normalized float64 samples.
5. Return `AnalysisResult`, or raise a typed `AnalysisError` for expected failures.

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
- API, database, storage, Celery orchestration, and observability are not implemented.
- The current API route is only a scaffold and must be replaced before production use.

## Planned deployment flow

```text
API -> persistent job -> queue -> analysis worker -> object storage -> API status
```

This flow is planned, not implemented. Its job IDs, retries, state transitions, and
storage contracts must be defined before API routes expose it.
