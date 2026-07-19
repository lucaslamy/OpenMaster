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

In progress: deterministic processor contract, composition pipeline, and gain staging.

Dependencies: completed v0.7 reference validation and `audio-core` extraction.

## v0.9 — Web application

Goal: deliver a Vue user interface for upload, job progress, analysis visualization,
and deterministic mastering controls.

Dependencies: typed API, authentication, storage, and job status from v0.7/v0.8.

## v1.0 — Automatic mastering

Goal: compose validated DSP processors into an auditable automatic-mastering workflow.

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
