# Changelog

All notable changes to OpenMaster are documented in this file.

## [Unreleased]

### Added

- Regression coverage for silent mono and 24-bit PCM WAV analysis.
- JSON command-line interface for deterministic local audio analysis.
- Controlled-signal regression coverage for BPM and musical-key estimation.
- FFmpeg/FFprobe decoder for AIFF, FLAC, M4A, MP3, OGG, and Opus input.
- End-to-end FLAC decoder regression coverage when FFmpeg is installed.
- FFmpeg decode duration bound derived from validated FFprobe metadata.
- IEEE-float 32/64-bit WAV decoding with finite-sample validation.

## [0.7.0-alpha.1] - 2026-07-19

### Added

- Typed, deterministic PCM WAV analysis service with safe input validation.
- CPU implementations for the v0.7 analysis measurements, including loudness,
  spectral, stereo, tempo, and key estimates.
- Synthetic WAV regression tests and Python quality-tool configuration.
- Repository ignore rules for generated Python and quality-tool artifacts.

### Changed

- Replaced the non-functional Librosa and Essentia placeholder backends.
