# Changelog

All notable changes to OpenMaster are documented in this file.

## [Unreleased]

### Fixed

- API/worker image now includes the Alembic runtime files and PostgreSQL driver required
  by the Helm migration Job.
- First installations now run Alembic after internal PostgreSQL becomes available,
  preventing the migration hook from reaching its deadline before data services exist.

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
