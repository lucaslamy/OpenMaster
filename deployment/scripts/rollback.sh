#!/usr/bin/env bash
set -Eeuo pipefail

NAMESPACE="${NAMESPACE:-openmaster}"
RELEASE="${RELEASE:-openmaster}"
TIMEOUT="${TIMEOUT:-10m}"
REVISION="${1:-}"
KUBE_CONTEXT="${KUBE_CONTEXT:-${NEW_CONTEXT:-default}}"

if [[ -n "${REVISION}" && ! "${REVISION}" =~ ^[0-9]+$ ]]; then
  printf 'Revision must be a positive integer.\n' >&2
  exit 2
fi

if [[ -n "${REVISION}" ]]; then
  helm rollback "${RELEASE}" "${REVISION}" --kube-context "${KUBE_CONTEXT}" --namespace "${NAMESPACE}" --wait --timeout "${TIMEOUT}"
else
  helm rollback "${RELEASE}" --kube-context "${KUBE_CONTEXT}" --namespace "${NAMESPACE}" --wait --timeout "${TIMEOUT}"
fi

kubectl --context "${KUBE_CONTEXT}" rollout status "deployment/${RELEASE}-openmaster-api" -n "${NAMESPACE}" --timeout="${TIMEOUT}"
kubectl --context "${KUBE_CONTEXT}" rollout status "deployment/${RELEASE}-openmaster-web" -n "${NAMESPACE}" --timeout="${TIMEOUT}"
