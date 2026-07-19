# OpenMaster 0.9.0

## Release scope

OpenMaster 0.9.0 releases the initial Vue web-client foundation. It provides a typed,
build-verified browser client for the analysis-job contract and complements the local
analysis and DSP packages.

## Included

- Vue 3 and TypeScript application in `apps/web`.
- Typed analysis-job HTTP client with idempotency-key submission.
- File-selection UI, non-terminal job polling, result rendering, and error display.
- Vitest coverage for client request and terminal-status behavior.
- Node 22 GitHub Actions test and production-build job.

## Verification

```bash
cd apps/web
npm ci
npm run test
npm run build
```

## Explicit non-goals

This release does not include a persistent backend job API, authentication, user job
history, rich visualizations, or browser-side mastering controls. The client is ready
to consume the documented analysis-job API once that backend delivery is complete.
