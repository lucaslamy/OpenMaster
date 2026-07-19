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

In progress: aligned stem groups can be rendered with one shared loudness decision and
one group peak-limiter envelope, preserving their sample-by-sample sum and balance.
The local CLI exports every named stem and its common decision record.
The CPU float64 backend remains the canonical implementation; an optional CuPy backend
can be selected explicitly for the same group-limiter operation.

## Planning rules

- Do not start a version by adding its UI before its package-level contracts exist.
- Prefer a vertical slice with tests over a broad layer of scaffolds.
- Add new work to this roadmap with an outcome, dependency, and measurable exit
  criterion.
