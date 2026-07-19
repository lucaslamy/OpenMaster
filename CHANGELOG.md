# Changelog

All notable changes to OpenMaster are documented in this file.

## [Unreleased]

### Changed

- Began `audio_core` extraction by centralizing reusable audio-input validation and
  resource limits.
- Added typed decoded-audio metadata and configurable decode-limit contracts.
- Moved PCM and IEEE-float WAV decoder ownership into `audio_core` with a compatible
  analysis-engine adapter.

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
