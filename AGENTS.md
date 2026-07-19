# AGENTS.md

> **Project:** OpenMaster
> **Purpose:** Development guidelines for human contributors and AI coding agents (Codex, ChatGPT, etc.)

---

# 1. Mission

OpenMaster is an open-source professional audio mastering platform.

The goal is **not** to reproduce iZotope Ozone feature-by-feature.

The goal is to build the best open-source mastering platform with:

* modern architecture
* modular DSP engine
* AI-assisted mastering
* Kubernetes-native deployment
* high test coverage
* production-grade quality

Every contribution should improve the long-term maintainability of the project.

---

# 2. Core Principles

## Code Quality

Prefer:

* readable code
* explicit code
* typed code
* modular code

Avoid:

* duplicated logic
* hidden side effects
* global mutable state
* overly clever implementations

---

## Simplicity

Always choose the simplest architecture that remains extensible.

Do not introduce abstraction before it becomes useful.

---

## Incremental Development

Every commit must leave the repository in a working state.

Never merge partially broken implementations.

---

## Production First

Every feature should be designed as if it will be deployed in production.

---

# 3. Technology Stack

## Backend

* Python 3.12+
* FastAPI
* SQLAlchemy 2.x
* Alembic
* Celery
* Redis

## Storage

* PostgreSQL
* MinIO

## Audio

* FFmpeg
* Essentia
* Librosa
* SoX

## AI

* PyTorch
* ONNX Runtime

GPU support is optional.

CPU execution must always work.

---

# 4. Monorepo Structure

```
apps/

    api/
    web/
    worker-analysis/
    worker-master/
    worker-export/

packages/

    audio-core/
    analysis-engine/
    dsp-engine/
    ai-engine/
    database/
    auth/
    storage/
    shared/

docs/

tests/

helm/

deployment/

sdk/
```

No application should directly depend on another application.

Shared logic belongs in packages.

---

# 5. Architecture Rules

Business logic must never live inside FastAPI routes.

Routes call services.

Services call packages.

Packages implement the actual logic.

Keep dependency direction simple.

---

# 6. Python Rules

Mandatory:

* Ruff
* Black
* MyPy
* PyTest

Every public function must be typed.

Every module must contain a short description.

Avoid files larger than approximately 600 lines.

Prefer composition over inheritance.

---

# 7. API Rules

Every endpoint must:

* validate inputs
* return typed responses
* expose OpenAPI documentation
* use proper HTTP status codes

Never return raw exceptions.

---

# 8. Database Rules

Use Alembic.

Every migration must be reversible.

Never modify production schemas manually.

Use UUIDs for primary identifiers unless justified otherwise.

---

# 9. Celery Rules

Tasks must be:

* idempotent
* retry-safe
* independently executable

Long-running tasks should report progress.

---

# 10. Kubernetes

Target:

* k3s
* Kubernetes upstream

Deployment must support:

* Helm
* Ingress
* Horizontal scaling
* Persistent volumes

No hardcoded hostnames.

---

# 11. Docker

Use multi-stage builds.

Keep images as small as possible.

Do not install unnecessary packages.

Run containers as non-root whenever practical.

---

# 12. Audio Processing Pipeline

Target pipeline:

1. Upload
2. Validation
3. Metadata extraction
4. Audio analysis
5. DSP chain
6. AI refinement
7. Export
8. Storage

Each stage must be independently testable.

---

# 13. Analysis Engine

Support:

* LUFS
* RMS
* Peak
* True Peak
* Dynamic Range
* Crest Factor
* BPM
* Key Detection
* Stereo Width
* Phase Correlation
* Spectral Centroid
* Sample Rate
* Bit Depth
* Duration

---

# 14. DSP Engine

Modules should remain independent.

Examples:

* EQ
* Dynamic EQ
* Compressor
* Multiband Compressor
* Exciter
* Saturation
* Stereo Imager
* Limiter
* Maximizer

Each processor should expose a consistent interface.

---

# 15. AI Engine

AI must never hide deterministic DSP.

The assistant should recommend settings.

The DSP engine remains deterministic and reproducible.

---

# 16. Testing

Minimum requirements:

* unit tests
* integration tests
* API tests

New features should include tests.

Bug fixes should include regression tests when appropriate.

---

# 17. Logging

Use structured logging.

Never log secrets.

Never log audio content.

---

# 18. Security

Secrets must come from environment variables or secret managers.

Never commit credentials.

Validate uploaded files before processing.

Reject unsupported formats.

---

# 19. Performance

Avoid unnecessary memory copies.

Stream large files where practical.

Profile before optimizing.

---

# 20. Git Workflow

Use Conventional Commits.

Examples:

```
feat:
fix:
refactor:
test:
docs:
perf:
ci:
build:
```

---

# 21. Semantic Versioning

Use:

MAJOR.MINOR.PATCH

Examples:

0.7.0

0.7.1

1.0.0

---

# 22. Documentation

Every major feature should include:

* purpose
* architecture
* usage
* examples
* limitations

---

# 23. Definition of Done

A task is complete only if:

* implementation finished
* tests passing
* documentation updated
* changelog updated
* formatting passes
* lint passes
* typing passes

---

# 24. Roadmap

## v0.7

Complete analysis engine.

## v0.8

Complete DSP chain.

## v0.9

Vue frontend.

## v1.0

Automatic mastering.

## v1.1

AI Master Assistant.

## v1.2

Reference Matching.

## v2.0

Stem mastering.

GPU acceleration.

Plugin system.

---

# 25. Rules for AI Coding Agents

When modifying the repository:

1. Understand the existing architecture before coding.
2. Prefer improving existing modules over creating duplicates.
3. Keep commits focused.
4. Refactor when it clearly improves maintainability.
5. Never leave intentionally broken code.
6. Keep the project buildable after every commit.
7. Update documentation whenever behavior changes.
8. Add tests for new behavior whenever practical.
9. Explain architectural trade-offs in commit messages or ADRs when significant.
10. Optimize for long-term maintainability over short-term speed.

OpenMaster should evolve as a professional open-source platform, not as a collection of isolated features.
