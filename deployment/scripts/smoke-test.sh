#!/usr/bin/env bash
set -Eeuo pipefail

NAMESPACE="${NAMESPACE:-openmaster}"
RELEASE="${RELEASE:-openmaster}"
API_SERVICE="${RELEASE}-openmaster-api"
WEB_SERVICE="${RELEASE}-openmaster-web"
KUBE_CONTEXT="${KUBE_CONTEXT:-${NEW_CONTEXT:-default}}"

command -v curl >/dev/null || {
  printf 'Missing required command: curl\n' >&2
  exit 1
}

TMP_DIR="$(mktemp -d)"
API_FORWARD_PID=""
WEB_FORWARD_PID=""
cleanup() {
  [[ -z "${API_FORWARD_PID}" ]] || kill "${API_FORWARD_PID}" 2>/dev/null || true
  [[ -z "${WEB_FORWARD_PID}" ]] || kill "${WEB_FORWARD_PID}" 2>/dev/null || true
  rm -rf -- "${TMP_DIR}"
}
trap cleanup EXIT INT TERM

kubectl --context "${KUBE_CONTEXT}" -n "${NAMESPACE}" port-forward \
  "service/${API_SERVICE}" 18000:8000 --address 127.0.0.1 \
  >"${TMP_DIR}/api-port-forward.log" 2>&1 &
API_FORWARD_PID="$!"

kubectl --context "${KUBE_CONTEXT}" -n "${NAMESPACE}" port-forward \
  "service/${WEB_SERVICE}" 18080:80 --address 127.0.0.1 \
  >"${TMP_DIR}/web-port-forward.log" 2>&1 &
WEB_FORWARD_PID="$!"

wait_for_http() {
  local url="$1"
  local log_file="$2"
  for _ in $(seq 1 30); do
    if curl --fail --silent --show-error "${url}" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  cat -- "${log_file}" >&2
  printf 'Smoke test timed out for %s\n' "${url}" >&2
  return 1
}

wait_for_http "http://127.0.0.1:18000/health/live" "${TMP_DIR}/api-port-forward.log"
wait_for_http "http://127.0.0.1:18000/health/ready" "${TMP_DIR}/api-port-forward.log"
wait_for_http "http://127.0.0.1:18080/" "${TMP_DIR}/web-port-forward.log"

printf 'API and web smoke tests passed in namespace %s.\n' "${NAMESPACE}"
