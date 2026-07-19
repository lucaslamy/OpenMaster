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

In progress: the baseline orchestration exposes its full ordered processor trace and
uses explicit gain and ceiling settings. It does not yet infer settings from analysis;
that requires validated processor-control policy and additional DSP processors.

Implemented policy slice: integrated loudness produces a target-gain recommendation,
bounded by a configurable safety limit and recorded with its requested value and reason.
Measured sample-peak headroom further constrains upward gain before rendering.

Exit criteria:

- Every automatic decision is serialized, bounded, and reproducible from analysis.
- The render trace identifies processor order and effective settings.
- Output validation covers peak safety, deterministic repeatability, and target
  loudness behavior.

## v1.1 — AI Master Assistant

Goal: recommend deterministic processor settings with explainable confidence and no
hidden DSP decisions.

## v1.2 — Reference matching

Goal: compare an input with a selected reference and produce bounded, explainable DSP
recommendations.

## v2.0 — Stems, acceleration, plugins

Goal: support stem mastering, optional GPU acceleration, and an isolated plugin system
without weakening deterministic CPU execution.

## Planning rules

- Do not start a version by adding its UI before its package-level contracts exist.
- Prefer a vertical slice with tests over a broad layer of scaffolds.
- Add new work to this roadmap with an outcome, dependency, and measurable exit
  criterion.
