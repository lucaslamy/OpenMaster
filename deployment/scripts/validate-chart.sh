#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
CHART="${ROOT_DIR}/helm/openmaster"
RENDERED="$(mktemp)"
trap 'rm -f "${RENDERED}"' EXIT

helm lint "${CHART}"

render() {
  helm template openmaster "${CHART}" --namespace openmaster "$@" >"${RENDERED}"
}

assert_absent() {
  if grep -Eq "$1" "${RENDERED}"; then
    printf 'Unexpected rendered pattern: %s\n' "$1" >&2
    exit 1
  fi
}

render -f "${CHART}/values.yaml"
grep -q 'kind: StatefulSet' "${RENDERED}"
assert_absent '(^|[[:space:]])(password|secret|token):[[:space:]]+[^<{[:space:]]'
grep -q 'name: openmaster-secrets' "${RENDERED}"

for service in postgresql redis minio; do
  case "${service}" in
    postgresql) host=postgres.example.internal ;;
    redis) host=redis.example.internal ;;
    minio) host=minio.example.internal ;;
  esac
  render -f "${CHART}/values.yaml" \
    --set "${service}.enabled=false" --set "${service}.externalHost=${host}"
  grep -Eq "externalName: \"?${host}\"?" "${RENDERED}"
done

render -f "${CHART}/values.yaml" \
  --set postgresql.enabled=false --set postgresql.externalHost=postgres.example.internal \
  --set redis.enabled=false --set redis.externalHost=redis.example.internal \
  --set minio.enabled=false --set minio.externalHost=minio.example.internal
[[ "$(grep -c 'type: ExternalName' "${RENDERED}")" -eq 3 ]]

render -f "${CHART}/values.yaml" --set networkPolicy.enabled=false
assert_absent 'kind: NetworkPolicy'
render -f "${CHART}/values.yaml" --set autoscaling.enabled=true \
  --set podDisruptionBudget.enabled=true
[[ "$(grep -c 'kind: HorizontalPodAutoscaler' "${RENDERED}")" -eq 4 ]]
[[ "$(grep -c 'kind: PodDisruptionBudget' "${RENDERED}")" -eq 5 ]]
grep -q 'readinessProbe:' "${RENDERED}"
grep -q 'resources:' "${RENDERED}"
grep -q 'allowPrivilegeEscalation: false' "${RENDERED}"

render -f "${CHART}/values.yaml" --set ingress.enabled=false
assert_absent 'kind: Ingress'
render -f "${CHART}/values.yaml" --set ingress.enabled=true \
  --set ingress.host=openmaster.example.com
grep -q 'kind: Ingress' "${RENDERED}"

if helm plugin list 2>/dev/null | grep -q '^unittest'; then
  helm unittest "${CHART}"
else
  printf 'helm-unittest is not installed; render assertions passed.\n'
fi

if command -v kubeconform >/dev/null; then
  render -f "${CHART}/values.yaml" -f "${CHART}/values-production.yaml"
  kubeconform -strict -ignore-missing-schemas "${RENDERED}"
else
  printf 'kubeconform is not installed; schema validation skipped.\n'
fi
