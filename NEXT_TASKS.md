Release target: v2.1

# Session handoff

## Current uncommitted state

- `helm/openmaster/templates/networkpolicy.yaml` is intentionally uncommitted. It
  currently contains an unsafe default-deny policy that lacks DNS, ingress-controller,
  and required workload traffic allowances. Do not deploy or commit it as-is.

## P0 — Complete safe NetworkPolicies

- **State:** Incomplete; uncommitted draft exists.
- **Files:** `helm/openmaster/templates/networkpolicy.yaml`, `helm/openmaster/values.yaml`.
- **Expected result:** Default deny scoped to OpenMaster pods, explicit DNS egress,
  ingress-controller-to-web/API ingress, API/workers-to-PostgreSQL/Redis/MinIO egress,
  and data-service ingress only from required callers. External dependency egress must
  be configurable rather than silently blocked.
- **Validation:** `helm lint helm/openmaster`; `helm template openmaster
  helm/openmaster --namespace openmaster -f helm/openmaster/values.yaml -f
  helm/openmaster/values-production.yaml`; Kubernetes schema validation when `kubectl`
  or `kubeconform` is available.

## P1 — Helm workload resilience and service modes

- **State:** Internal services and ExternalName modes are implemented; no automated
  internal/external render assertions yet.
- **Files:** `helm/openmaster/templates/data-services.yaml`, `helm/openmaster/values.yaml`,
  `helm/openmaster/values-production.yaml`, Helm tests to add under
  `helm/openmaster/templates/tests/`.
- **Expected result:** Verify PostgreSQL, Redis, and MinIO internal and external renders;
  make storage classes, persistence, resource limits, and secret requirements explicit.
- **Validation:** Helm lint/template for all six enabled/disabled combinations.

## P1 — HPA, PDB, and migration operational controls

- **State:** Not implemented.
- **Files:** `helm/openmaster/templates/hpa.yaml`, `helm/openmaster/templates/pdb.yaml`,
  `helm/openmaster/values.yaml`, `helm/openmaster/templates/migration-job.yaml`.
- **Expected result:** Optional HPA for API/workers, PDB for stateless deployments, and
  migration Job concurrency/TTL/security settings.
- **Validation:** Helm lint/template with autoscaling enabled and disabled.

## P1 — Deployment scripts and secret preflight

- **State:** Not implemented.
- **Files:** `deployment/scripts/preflight-check.sh`, `deploy.sh`, `rollback.sh`,
  `smoke-test.sh`, `deployment/examples/*.example.yaml`, `deployment/README.md`.
- **Expected result:** Shell scripts use `set -Eeuo pipefail`, never print secret values,
  verify expected secret keys by name only, lint/template chart, deploy, wait rollouts,
  and smoke-test health endpoints.
- **Validation:** `shellcheck deployment/scripts/*.sh`; execute preflight against an
  authorized cluster only.

## P2 — CI and deployment documentation

- **State:** Not implemented.
- **Files:** `.github/workflows/*`, `docs/deployment/k3s.md`,
  `docs/deployment/vault-external-secrets.md`,
  `docs/deployment/production-checklist.md`, `docs/deployment/troubleshooting.md`,
  `helm/openmaster/README.md`.
- **Expected result:** Helm/Docker CI, non-production manual deploy workflow, and complete
  k3s/Vault deployment instructions with all replaceable values and secret key names.
- **Validation:** GitHub Actions syntax review, Helm lint/template, Docker builds when
  registry/network access is available.

## P2 — Release v2.1

- **State:** Not started.
- **Files:** `pyproject.toml`, `apps/web/package.json`,
  `apps/web/package-lock.json`, `README.md`, `ROADMAP.md`, `ARCHITECTURE.md`,
  `CHANGELOG.md`.
- **Expected result:** Release only after every P0/P1 task passes validation; update
  version, docs, changelog, tag, and remove completed tasks from this file.
- **Validation:** Full Python suite, frontend tests/build, Helm validation, shellcheck,
  and available Kubernetes manifest validation.
