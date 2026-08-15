#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
CHART="${CHART:-${ROOT_DIR}/helm/openmaster}"
NAMESPACE="${NAMESPACE:-openmaster}"
RELEASE="${RELEASE:-openmaster}"
VALUES="${VALUES:-${CHART}/values-production.yaml}"
TIMEOUT="${TIMEOUT:-10m}"
KUBE_CONTEXT="${KUBE_CONTEXT:-${NEW_CONTEXT:-default}}"

"${ROOT_DIR}/deployment/scripts/preflight-check.sh"
helm upgrade --install "${RELEASE}" "${CHART}" --kube-context "${KUBE_CONTEXT}" --namespace "${NAMESPACE}" \
  --create-namespace -f "${CHART}/values.yaml" -f "${VALUES}" \
  --atomic --wait --timeout "${TIMEOUT}"

for component in api web analysis-worker mastering-worker export-worker; do
  kubectl --context "${KUBE_CONTEXT}" rollout status "deployment/${RELEASE}-openmaster-${component}" \
    -n "${NAMESPACE}" --timeout="${TIMEOUT}"
done

"${ROOT_DIR}/deployment/scripts/smoke-test.sh"
