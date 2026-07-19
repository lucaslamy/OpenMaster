#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
CHART="${CHART:-${ROOT_DIR}/helm/openmaster}"
NAMESPACE="${NAMESPACE:-openmaster}"
RELEASE="${RELEASE:-openmaster}"
VALUES="${VALUES:-${CHART}/values-production.yaml}"
TIMEOUT="${TIMEOUT:-10m}"

"${ROOT_DIR}/deployment/scripts/preflight-check.sh"
helm upgrade --install "${RELEASE}" "${CHART}" --namespace "${NAMESPACE}" \
  --create-namespace -f "${CHART}/values.yaml" -f "${VALUES}" \
  --atomic --wait --timeout "${TIMEOUT}"

for component in api web analysis-worker mastering-worker export-worker; do
  kubectl rollout status "deployment/${RELEASE}-openmaster-${component}" \
    -n "${NAMESPACE}" --timeout="${TIMEOUT}"
done

"${ROOT_DIR}/deployment/scripts/smoke-test.sh"
