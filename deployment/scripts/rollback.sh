#!/usr/bin/env bash
set -Eeuo pipefail

NAMESPACE="${NAMESPACE:-openmaster}"
RELEASE="${RELEASE:-openmaster}"
TIMEOUT="${TIMEOUT:-10m}"
REVISION="${1:-}"

if [[ -n "${REVISION}" && ! "${REVISION}" =~ ^[0-9]+$ ]]; then
  printf 'Revision must be a positive integer.\n' >&2
  exit 2
fi

if [[ -n "${REVISION}" ]]; then
  helm rollback "${RELEASE}" "${REVISION}" --namespace "${NAMESPACE}" --wait --timeout "${TIMEOUT}"
else
  helm rollback "${RELEASE}" --namespace "${NAMESPACE}" --wait --timeout "${TIMEOUT}"
fi

kubectl rollout status "deployment/${RELEASE}-openmaster-api" -n "${NAMESPACE}" --timeout="${TIMEOUT}"
kubectl rollout status "deployment/${RELEASE}-openmaster-web" -n "${NAMESPACE}" --timeout="${TIMEOUT}"
