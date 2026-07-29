#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
CHART="${CHART:-${ROOT_DIR}/helm/openmaster}"
NAMESPACE="${NAMESPACE:-openmaster}"
RELEASE="${RELEASE:-openmaster}"
VALUES="${VALUES:-${CHART}/values-production.yaml}"
SECRET_NAME="${SECRET_NAME:-openmaster-secrets}"
RENDERED="$(mktemp)"
trap 'rm -f "${RENDERED}"' EXIT

required=(helm kubectl)
for command_name in "${required[@]}"; do
  command -v "${command_name}" >/dev/null ||
    { printf 'Missing required command: %s\n' "${command_name}" >&2; exit 1; }
done

helm lint "${CHART}"
helm template "${RELEASE}" "${CHART}" --namespace "${NAMESPACE}" \
  -f "${CHART}/values.yaml" -f "${VALUES}" >"${RENDERED}"

kubectl auth can-i get secrets -n "${NAMESPACE}" >/dev/null ||
  { printf 'Current identity cannot read Secret metadata in namespace %s\n' "${NAMESPACE}" >&2; exit 1; }
kubectl get secret "${SECRET_NAME}" -n "${NAMESPACE}" >/dev/null

required_keys=(
  DATABASE_URL CELERY_BROKER_URL CELERY_RESULT_BACKEND POSTGRES_DB POSTGRES_USER
  POSTGRES_PASSWORD MINIO_ROOT_USER MINIO_ROOT_PASSWORD MASTERING_ACCESS_PASSWORD
  OPENMASTER_ADMIN_EMAIL OPENMASTER_ADMIN_PASSWORD
)
for key in "${required_keys[@]}"; do
  kubectl get secret "${SECRET_NAME}" -n "${NAMESPACE}" \
    -o "jsonpath={.data.${key}}" | grep -q . ||
    { printf 'Secret %s is missing required key %s\n' "${SECRET_NAME}" "${key}" >&2; exit 1; }
done

if grep -q 'OPENMASTER_REMOTE_COMPUTE_ENABLED: "true"' "${RENDERED}"; then
  kubectl get secret "${SECRET_NAME}" -n "${NAMESPACE}" \
    -o 'jsonpath={.data.RUNPOD_API_KEY}' | grep -q . ||
    { printf 'Secret %s is missing required key RUNPOD_API_KEY\n' "${SECRET_NAME}" >&2; exit 1; }
fi

if grep -q 'LAMAI_ENABLED: "true"' "${RENDERED}"; then
  kubectl get secret "${SECRET_NAME}" -n "${NAMESPACE}" \
    -o 'jsonpath={.data.LAMAI_API_KEY}' | grep -q . ||
    { printf 'Secret %s is missing required key LAMAI_API_KEY\n' "${SECRET_NAME}" >&2; exit 1; }
fi

printf 'Preflight checks passed for release %s in namespace %s.\n' "${RELEASE}" "${NAMESPACE}"
