# Changelog

All notable changes to OpenMaster are documented in this file.

## [Unreleased]

## [3.0.2] - 2026-07-26

### Added

- Lightweight password-only authorization endpoint issuing a signed 60-second
  mastering proof before any audio upload begins.

### Changed

- Incorrect passwords now produce an immediate localized error inside the still-open
  authorization dialog; the password field is cleared and no upload, job, Celery task,
  RunPod request, credit, or quota is consumed.
- Initial and final render creation require the signed proof, preventing callers from
  bypassing the preliminary password check.

## [3.0.1] - 2026-07-26

### Added

- AudioWorklet preview for loudness-target gain, maximum correction, normalized soft
  clipping, saturation, lookahead/release limiting, and dithered 16/24/32-bit
  quantization audition without backend rendering.
- Visible preset-character descriptions and a regression test ensuring driven masters
  increase programme loudness while retaining the configured true-peak ceiling.

### Changed

- Rap now targets −9 LUFS and −1 dBTP with 12 dB correction headroom, stronger low-end
  weight, restrained spectral reduction, lighter 2 dB clipping, and subtle saturation.
- Clipper normalization now preserves programme level as drive increases.
- Automatic loudness gain is no longer blocked by raw input peaks before the clipper
  and true-peak limiter; the final limiter remains responsible for peak safety.
- The default LamAI service and matching NetworkPolicy test now use port `8080`.

## [3.0.0] - 2026-07-26

### Added

- Real-time Web Audio preview with smoothed EQ, high-pass, light dynamics, reset, and
  position-preserving A/B bypass.
- Central parameter metadata and idempotent final-render jobs reusing source and analysis.
- Reversible Alembic revision `0010` and settings/final-render API operations.

### Changed

- The studio is now a centered responsive single-column workflow.
- Password validation occurs from the POST body before upload, persistence, or dispatch.

## [2.9.0] - 2026-07-26

### Added

- Auditable LamAI mastering comparison with exact settings before and after AI advice,
  localized change cards, rationale, model identity, and explicit fallback state.

## [2.8.0] - 2026-07-26

### Added

- Optional LamAI mastering adviser that receives only structured analysis measurements,
  returns a strictly validated bounded policy, and falls back to the original
  deterministic settings when the private AI gateway is unavailable.
- Persisted web opt-in, server-side Bearer authentication, local/RunPod policy
  propagation, Helm and NetworkPolicy configuration, and reversible Alembic revision
  `0009`.

## [2.7.0] - 2026-07-26

### Added

- Persisted three-band tonal EQ controls with an interactive web response preview,
  translated explanations, safe ±6 dB bounds, and identical local/RunPod rendering.
- Four-times oversampled soft clipper with profile-aware drive and an explicit
  zero-drive bypass.
- Linked four-times oversampled True Peak limiter with configurable lookahead and
  release, reconstructed-peak validation, and deterministic processor audit records.
- Reversible Alembic revision `0006` for the advanced mastering policy.
- Persisted original/master spectral-balance profiles and windowed RMS histories with
  fixed dBFS scales, interactive interpolation, bilingual explanations, and reversible
  Alembic revision `0007`.
- Complete deterministic mastering chain with a 24 dB/octave subsonic high-pass,
  frequency-selective dynamic EQ, linked bass control, de-essing, and oversampled
  light saturation before the existing clipper and True Peak limiter.
- Post-render integrated LUFS and reconstructed True Peak measurements, plus
  deterministic TPDF dither during integer PCM export.
- Six persisted local/RunPod controls for the new stages, bilingual web explanations,
  and reversible Alembic revision `0008`.

### Changed

- Rap, Club, Loud, Podcast, Streaming, Dynamic, and Transparent profiles now select
  explicit tonal and transient-processing starting points in addition to delivery
  loudness, ceiling, correction bounds, and bit depth.

## [2.6.0] - 2026-07-26

### Added

- Complete English/French interface selector with persistent locale, technically
  reviewed French mastering terminology, translated guide, controls, analysis views,
  accessibility labels, and assistant findings.
- Selectable Rap mastering profile using a transparent −10 LUFS target, −0.8 dBFS
  ceiling, ±9 dB correction bound, and 24-bit WAV delivery.
- Three interactive original/master comparison graphs with independent reveal sliders:
  absolute peak envelope, moving peak density, and point-to-point transient activity.
- Guide documentation explaining how each comparison is derived and why these compact
  views must not be interpreted as LUFS histories, spectra, or exact dynamics meters.
- Server-enforced mastering password using a Vault-provided secret, constant-time API
  comparison, and a bilingual password dialog opened only when mastering is requested.

### Changed

- Waveform envelopes now retain peak amplitude relative to digital full scale instead
  of normalizing source and master independently; comparison sliders morph the actual
  curve geometry point by point and keep faint endpoint references visible.
- Mastering settings use a denser preset grid, an active-policy summary, and a focused
  authorization dialog for a shorter and clearer submission flow.

## [2.5.0] - 2026-07-25

### Added

- Six truthful analysis views for overview, levels, dynamics, stereo, spectral centroid,
  and source metadata, derived exclusively from persisted analysis measurements.
- Transparent, Streaming, Podcast, Club, Loud, and Dynamic mastering intentions that
  apply editable combinations of target LUFS, peak ceiling, gain bound, and WAV depth.
- Accessible hover/focus explanations for every mastering control and key sound metric.
- Integrated field-guide page covering the processing pipeline, measurement glossary,
  mastering controls, limitations, and practical delivery starting points.
- Real headroom, correction-strength, and output-resolution safeguard switches backed
  by the existing deterministic mastering policy rather than hidden processing.
- Persisted source/master waveform envelopes and an A/B player with synchronized
  switching and a draggable before/after waveform reveal.
- Retry-stable WAV names derived from the original filename, selected bit depth, and
  job timestamp, plus separate inline preview and attachment download URLs.
- Alembic revision `0005` for durable source and master waveform envelopes.

### Changed

- The in-app guide now explains integrated LUFS, perceptual weighting, silence gating,
  peak-ceiling interactions, practical targets, and playback normalization.

## [2.4.0] - 2026-07-25

### Added

- Responsive mastering-studio interface with local drag-and-drop waveform preview,
  source playback, mastering-profile presets, bit-depth controls, pipeline progress,
  readable analysis cards, assistant findings, and a dedicated master delivery panel.
- Typed presentation helpers and frontend regression tests for durable job progress,
  safe metric formatting, and assistant recommendation rendering.
- Real mastering controls for limiter ceiling and maximum gain correction, persisted
  in PostgreSQL and applied consistently by local and RunPod DSP execution.
- Expanded in-progress analysis dashboard with RMS, sample peak, peak headroom, phase,
  channel/bit-depth/sample-rate metadata, active policy, and bounded visual meters.
- Alembic revision `0004` for durable mastering-policy settings.

### Fixed

- Main Helm Ingress now renders configured annotations, allowing ingress-nginx upload
  size, request-buffering, and timeout settings to reach the deployed resource.

## [2.3.1] - 2026-07-25

### Fixed

- Broker readiness no longer imports the complete Celery, DSP, and audio worker graph,
  keeping the `wait-for-broker` init container below its 64 MiB memory limit.

## [2.3.0] - 2026-07-25

### Added

- End-to-end web workflow from one audio upload through deterministic analysis,
  explainable mastering recommendation, local or RunPod mastering, private MinIO
  publication, and short-lived master download.
- Web controls for target loudness and 16-, 24-, or 32-bit WAV output, with durable
  analysis, recommendation, mastering, failure, and download states.
- Alembic revision `0003` for mastering settings, recommendation and render audit
  records, and the final MinIO object identifier.

### Fixed

- Celery workers now wait for Redis to accept connections in an init container,
  removing the normal k3s startup race that previously produced repeated
  `Connection refused` messages after a fresh deployment.

## [2.2.0] - 2026-07-25

### Added

- Optional RunPod Serverless client and hardened remote mastering worker using bounded
  signed-URL transfers, source SHA-256 verification, asynchronous status polling, and
  an explicit local CPU fallback boundary.
- Helm configuration, secret preflight, NetworkPolicy egress control, container image,
  tests, and deployment guidance for pay-per-use remote compute.
- Dedicated TLS Ingress for the internal MinIO API port, Traefik-to-MinIO network policy,
  and application-side signed GET/PUT URLs for RunPod object transfers.
- Shared cross-namespace MinIO support with an external HTTPS endpoint, label-based
  egress policy, and a corrected ClipForge/OpenMaster deployment example.

### Fixed

- API, migration, RunPod, and Celery worker containers now use the explicit
  non-root UID/GID `10001`, allowing kubelet to enforce `runAsNonRoot`.
- PostgreSQL now initializes persistent-volume ownership in a capability-limited
  init container before starting the database as UID/GID `70`.
- Web, API, migration, and Celery workloads now mount bounded writable temporary
  storage while retaining a read-only root filesystem.
- API startup, readiness, and liveness probes remain attached to the container
  after adding writable temporary storage.
- The web client now sends analysis requests through the `/api` ingress route and
  reports non-JSON proxy responses without exposing a JSON parser error.
- Durable `/api/v1/analysis-jobs` upload and polling, private MinIO source storage,
  PostgreSQL result persistence, and Celery object analysis with FFmpeg in the shared
  API/worker image.
- API/worker image now includes the Alembic runtime files and PostgreSQL driver required
  by the Helm migration Job.
- First installations now run Alembic after internal PostgreSQL becomes available,
  preventing the migration hook from reaching its deadline before data services exist.
- Internal PostgreSQL, Redis, and MinIO now use explicit non-root UID/GID settings
  compatible with their images, including a writable PostgreSQL socket directory.

## [2.1.0] - 2026-07-19

### Added
- FastAPI production boundary with Kubernetes-safe liveness and readiness endpoints and
  a non-root multi-stage API image.
- Initial k3s Helm chart foundation with secret-free values, Vault-managed Secret name
  validation, non-sensitive ConfigMap, and hardened ServiceAccount.
- Dedicated Helm deployments for the retry-safe analysis, mastering, and export Celery
  queues with isolated resource and concurrency settings.
- Production web image and Helm workload, plus Traefik routing for the frontend root.
- Internal PostgreSQL, Redis, and MinIO Helm services with persistent state where
  required, probes, and hardened pod security defaults.
- Reversible Alembic baseline migration and Helm Job for serialized database upgrades
  using the Vault-managed runtime Secret.
- Complete internal and ExternalName modes for PostgreSQL, Redis, and MinIO with
  configurable persistence, resources, probes, and explicit external egress CIDRs.
- Least-privilege NetworkPolicies for DNS, ingress, workloads, and data-service callers,
  with a supported disable switch and no implicit all-address egress.
- Optional API/worker HPA resources and stateless-workload disruption budgets.
- Secret-safe preflight, atomic deployment, rollback, smoke-test, and chart-validation
  scripts.
- Helm render assertions, CI lint/unit/schema/shell validation, and complete k3s, Vault,
  production, and troubleshooting documentation.

## [2.0.0] - 2026-07-19

### Added

- Balance-preserving aligned stem-group mastering with one shared automatic policy and
  one linked group sample-peak limiter envelope.
- Local stem-group mastering CLI with atomic named WAV exports and a serialized shared
  decision record.
- Explicit CPU reference and optional CuPy GPU compute backends for the shared stem-group
  limiter operation, with no implicit device fallback.
- Isolated external DSP plugin processor with explicit manifests, timeout-bounded
subprocess execution, and strict NPY/JSON input-output validation.

## [1.2.0] - 2026-07-19

### Added

- Local reference-matching service with bounded reference-loudness targets, serialized
  comparison metrics, and explainable spectral and stereo review findings.
- Local reference-matching CLI that analyzes both files once and emits a versioned JSON
  comparison document without applying implicit EQ or stereo processing.
- Reference-match regression coverage for deterministic repeatability and policy-bounded
  gain recommendations.

## [1.1.0] - 2026-07-19

### Added

- Deterministic mastering-assistant recommendations with serialized policy and settings,
  bounded confidence, and explicit loudness, headroom, and phase findings.
- Local assistant CLI that emits analysis and reviewable mastering recommendations as
  stable JSON without modifying audio.
- Versioned assistant-recommendation JSON schema for explicit automation compatibility.

## [1.0.0] - 2026-07-19

### Added

- Traceable deterministic mastering baseline that applies explicit gain staging and
  linked sample-peak protection, and returns the processor order with rendered audio.
- Bounded automatic loudness-gain policy with an auditable requested/effective setting
  record and a deterministic render integration.
- Automatic gain now considers measured sample-peak headroom before rendering, reducing
  avoidable limiter engagement.
- Atomic PCM WAV export for 16-, 24-, and 32-bit mastered output with overwrite and
  normalized-sample safety checks.
- End-to-end automatic-mastering WAV export returning the render trace and decision
  record alongside the committed destination.
- Local automatic-mastering CLI that decodes once, analyses, renders, exports WAV, and
  emits a stable JSON audit record.
- Automatic mastering decision records now include the complete policy that produced
  them, and regression coverage verifies deterministic target-loudness rendering and
  sample-peak safety.

### Changed

- Analysis service can analyse an already decoded stream, eliminating redundant decoding
  for composed workflows such as automatic mastering.

## [0.9.0] - 2026-07-19

### Added

- Initial Vue and TypeScript web client with typed analysis-job submission flow.
- Node 22 CI checks for the Vue client test and production build.
- Automatic analysis-job polling and result rendering in the Vue client.

## [0.8.0] - 2026-07-19

### Added

- Initial v0.8 deterministic DSP processor contract, composition pipeline, and gain
  staging processor.
- Linked deterministic sample-peak limiter with stereo-link regression coverage.

## [0.7.0] - 2026-07-19

### Changed

- Began `audio_core` extraction by centralizing reusable audio-input validation and
  resource limits.
- Added typed decoded-audio metadata and configurable decode-limit contracts.
- Moved PCM and IEEE-float WAV decoder ownership into `audio_core` with a compatible
  analysis-engine adapter.
- Corrected stereo integrated-loudness energy summation.
- Corrected half-tempo selection for controlled high-tempo click tracks.
- Moved FFmpeg decoding ownership into `audio_core` with a compatible analysis-engine
  adapter.
- Delegated all analysis input decoding through the `audio_core` format dispatcher.
- Added FFmpeg ebur128 cross-validation for mono and dual-mono loudness and true peak.
- Added pure, typed retry-safe analysis-job lifecycle contracts.

## [0.7.0-rc.1] - 2026-07-19

### Added

- Regression coverage for silent mono and 24-bit PCM WAV analysis.
- JSON command-line interface for deterministic local audio analysis.
- Controlled-signal regression coverage for BPM and musical-key estimation.
- FFmpeg/FFprobe decoder for AIFF, FLAC, M4A, MP3, OGG, and Opus input.
- End-to-end format-matrix coverage for all FFmpeg-supported input formats.
- FFmpeg decode duration bound derived from validated FFprobe metadata.
- IEEE-float 32/64-bit WAV decoding with finite-sample validation.
- GitHub Actions quality workflow for formatting, linting, typing, and tests.
- Root-level roadmap and architecture documentation, plus completed agent guidance.
- Explicit setuptools package discovery for installable shared Python packages.
- Ignore generated Python build metadata and distributions.

## [0.7.0-alpha.1] - 2026-07-19

### Added

- Typed, deterministic PCM WAV analysis service with safe input validation.
- CPU implementations for the v0.7 analysis measurements, including loudness,
  spectral, stereo, tempo, and key estimates.
- Synthetic WAV regression tests and Python quality-tool configuration.
- Repository ignore rules for generated Python and quality-tool artifacts.

### Changed

- Replaced the non-functional Librosa and Essentia placeholder backends.
