# OpenMaster roadmap

This roadmap is the delivery order for OpenMaster. A version is complete only when its
scope meets the definition of done in `AGENTS.md`; a feature is not complete merely
because a scaffold exists.

## v0.7 — Analysis engine

Goal: provide a deterministic, locally executable analysis foundation.

Released: `0.7.0`. Its supported scope is the deterministic local analysis engine; it
is not a mastering-compliance or distributed-service release.

Completed:

- Typed analysis result and input-error model.
- PCM and IEEE-float WAV decoding.
- FFmpeg/FFprobe decoding for AIFF, FLAC, M4A, MP3, OGG, and Opus.
- LUFS, RMS, peak, true peak, dynamic range, crest factor, BPM, key, stereo, phase,
  spectral-centroid, and source metadata measurements.
- JSON command-line interface, regression tests, and Python quality CI.

Post-release hardening:

- Validate every measurement against an approved reference corpus and document error
  tolerances, especially LUFS, true peak, BPM, and musical key.
- Stream long audio rather than retaining the entire decoded signal in memory.
- Complete long-file streaming and shared export primitives in `audio_core`; decoder,
  metadata, input validation, and resource-limit contracts are now extracted.
- Expose the analysis job through a typed API, persistent job model, and worker.

Current validation: deterministic synthetic signals and FFmpeg ebur128 cross-validation
protect the local implementation. An approved external corpus remains required for
compliance or real-music accuracy claims.

## v0.8 — Deterministic DSP chain

Goal: provide independently testable EQ, compression, stereo, saturation, limiting,
and export processors with reproducible parameter sets.

Released: `0.8.0`. Its supported scope is the deterministic processor foundation,
composition pipeline, fixed gain staging, and linked sample-peak limiting.

Post-release DSP work: parametric EQ, compressor, stereo imager, saturation, a
lookahead true-peak limiter, and export primitives.

Dependencies: completed v0.7 reference validation and `audio-core` extraction.

## v0.9 — Web application

Goal: deliver a Vue user interface for upload, job progress, analysis visualization,
and deterministic mastering controls.

Released: `0.9.0`. Its supported scope is the typed Vue analysis-job client with upload,
polling, result rendering, and Node CI.

Post-release web work: persistent API integration, authentication, rich analysis
visualization, accessible job-history views, and deterministic mastering controls.

Dependencies: typed API, authentication, storage, and job status from v0.7/v0.8.

## v1.0 — Automatic mastering

Goal: compose validated DSP processors into an auditable automatic-mastering workflow.

Released: `1.0.0`. Its supported scope is deterministic automatic gain staging from
integrated loudness, bounded by policy and sample-peak headroom, followed by a linked
sample-peak safety limiter and PCM WAV export.

Completed:

- One-decode local workflow: analysis, bounded decision, render, and atomic WAV export.
- Serialized policy, requested and effective gain, peak-headroom constraint, and ordered
  processor trace in the result and CLI JSON audit record.
- Deterministic repeatability, sample-peak safety, and controlled-signal target-loudness
  regression coverage.

Post-release mastering work: parametric EQ, compressor, stereo imager, saturation, and
a lookahead true-peak limiter. v1.0 is not a loudness-compliance or true-peak guarantee.

## v1.1 — AI Master Assistant

Goal: recommend deterministic processor settings with explainable confidence and no
hidden DSP decisions.

Released: `1.1.0`. Its supported scope is a deterministic local mastering assistant,
not remote or generative model inference.

Completed:

- Explicit recommended policy and effective v1.0 settings derived from immutable
  analysis results.
- Deterministic confidence score with documented deductions for unavailable loudness,
  constrained peak headroom, and unavailable stereo evidence.
- Human-readable loudness, safety-bound, headroom, and phase findings; no hidden DSP
  processing or settings.
- Versioned recommendation JSON schema and local one-decode assistant CLI.

Post-release assistant work: optional model-backed natural-language advice must remain
bounded by this explicit recommendation contract and preserve offline deterministic use.

## v1.2 — Reference matching

Goal: compare an input with a selected reference and produce bounded, explainable DSP
recommendations.

Released: `1.2.0`. Its supported scope is bounded local reference-aware loudness
recommendation and reviewable measurement comparison.

Completed:

- One-decode-per-file input/reference comparison for loudness, dynamic range, spectral
  centroid, stereo width, and phase correlation.
- Reference loudness target constrained to an explicit safe range; gain constrained by
  the existing v1.1 assistant policy and peak safety limits.
- Versioned comparison document and CLI containing every policy, delta, recommendation,
  confidence score, and review finding.
- Deterministic repeatability and policy-bound regression coverage.

Post-release matching work: validated EQ, dynamics, and stereo-imaging processors may
consume these review findings only through new explicit, independently tested settings.

## v2.0 — Stems, acceleration, plugins

Goal: support stem mastering, optional GPU acceleration, and an isolated plugin system
without weakening deterministic CPU execution.

Released: `2.0.0`. Its supported scope is aligned stem-group rendering, explicit optional
GPU execution of the group limiter, and external plugin isolation.

Completed:

- Named, aligned stem groups receive one shared automatic decision and sample-peak
  limiter envelope; their sum and balance are preserved and CLI outputs are atomic WAVs.
- NumPy float64 CPU backend remains canonical; an optional CuPy GPU implementation must
  be selected explicitly and fails clearly when its dependency is unavailable.
- Explicit plugin manifests run commands in timeout-bounded subprocesses using NPY audio
  and JSON configuration; host-side validation rejects malformed, non-finite, or
  shape-changing output.

Post-release v2 work: validate CPU/GPU equivalence on supported GPU hardware, add signed
plugin distribution and permissions, and broaden stem session metadata without weakening
the alignment and deterministic-rendering contracts.

## v3.0 — Unified interactive mastering

Released: `3.0.0`. The single-column web workflow adds an approximate local Web Audio
preview. Final renders reuse stored source audio and analysis and retain initial-master
lineage.

Patch `3.0.1` extends the local preview through an AudioWorklet and corrects loudness
gain staging plus the Rap starting point.

Patch `3.0.2` moves password validation ahead of audio transfer through a short-lived
signed authorization proof and keeps authentication failures inside the dialog.

## v3.1 — Durable projects and pre-master decision

Released: `3.1.0`. Analysis now pauses before mastering so the source can be auditioned
with live DSP and settings can be committed explicitly. The web studio exposes the
twenty newest durable root projects backed by PostgreSQL and retained MinIO objects.

## v3.2 — Persistent mastering studio

Released: `3.2.0`. The workspace uses the full viewport, keeps the original/live
preview transport reachable while settings scroll, moves retained projects into a
compact drawer, refreshes expiring media URLs, and keeps completed masters immutable.

## v3.3 — Measured upload and Rap Reloaded

Released: `3.3.0`. This version adds real source-upload byte progress, separates server
acceptance from transfer, and scrolls completed mastering jobs to the Before / after audit. The new
Rap Reloaded preset is calibrated from measured original/master audio while the
existing Rap preset remains available. Browser gain staging now uses analyzed source
loudness and no longer substitutes a broadband compressor for selective dynamics.

## v3.4 — Autonomous LamAI policy and mastering reference

Released: `3.4.0`. LamAI now derives every adjustable policy value independently from
measured evidence instead of treating the selected preset as a preference. Fixed DSP
topology remains server-enforced. The release also adds the complete sound-engineer
technical reference, repairs the audit layout, embeds the spectral-dynamics heading in
its control box, and opens source-code documentation in isolated browser tabs.

Patch `3.4.1` separates the RunPod image repository from the private API/web registry
root in the synchronized build-and-push workflow.

## v3.5 — Interactive engineering reference

Released: `3.5.0`. The web client now provides a dedicated bilingual sound-engineer
reference with responsive animated diagrams for the exact DSP order, measurements,
linked spectral dynamics, peak processing, LamAI validation boundary, presets, preview
differences, and PCM delivery. The studio gains pointer-reactive lighting, spectral
motion, animated metering, and panel depth while preserving reduced-motion behavior.
The exhaustive repository reference remains the normative companion document.

## v3.6 — Private accounts and administrator approval

Released: `3.6.0`. Database-backed accounts use revocable browser sessions and require
administrator approval before first login. The administrator is bootstrapped from
deployment secrets and reviews pending requests in a dedicated web view. SQL-enforced
ownership protects retained projects and every source, preview, settings, render, and
download operation. Settings section headings now render consistently across browsers
without changing their DSP controls.

Patch `3.6.1` normalizes every mastering-settings title as a `control-heading` legend
and reserves full-width separators for boxes containing several related controls.

Next release UI follow-up: remove the source-code link from the primary navigation and
move it to a quieter, still discoverable location such as the global footer or the
technical-reference page. It must continue to open GitHub in a separate isolated tab.

## Planning rules

- Do not start a version by adding its UI before its package-level contracts exist.
- Prefer a vertical slice with tests over a broad layer of scaffolds.
- Add new work to this roadmap with an outcome, dependency, and measurable exit
  criterion.

## Deployment follow-up

- v2.1 released: production k3s/Helm deployment with internal/external data-service
  modes, Vault External Secrets integration, least-privilege NetworkPolicies, Alembic
  migration hook, HPA/PDB controls, operational scripts, CI validation, and runbooks.
- TODO: migrate the production ingress configuration from Traefik to NGINX Ingress when
  the target cluster standardizes on NGINX; preserve `/api` and `/` routing, TLS,
  upload-size limits, and timeout behavior, then validate the rendered manifests.
