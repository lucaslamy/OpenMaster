# Changelog

All notable changes to OpenMaster are documented in this file.

## [0.7.0-alpha.1] - 2026-07-19

### Added

- Typed, deterministic PCM WAV analysis service with safe input validation.
- CPU implementations for the v0.7 analysis measurements, including loudness,
  spectral, stereo, tempo, and key estimates.
- Synthetic WAV regression tests and Python quality-tool configuration.
- Repository ignore rules for generated Python and quality-tool artifacts.

### Changed

- Replaced the non-functional Librosa and Essentia placeholder backends.
