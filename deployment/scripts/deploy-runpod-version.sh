#!/usr/bin/env bash
# Pin one OpenMaster version in RunPod values and deploy it atomically.

set -Eeuo pipefail

usage() {
  cat <<'EOF'
Usage: deployment/scripts/deploy-runpod-version.sh VERSION

Optional environment:
  VALUES=/tmp/openmaster-k3s-runpod.yaml
  REGISTRY=harbor.lucaslamy.fr/private/openmaster
  NAMESPACE=openmaster RELEASE=openmaster SECRET_NAME=openmaster-secrets TIMEOUT=20m
EOF
}

[[ $# -eq 1 ]] || { usage >&2; exit 2; }
VERSION="$1"
[[ "${VERSION}" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$ ]] ||
  { printf 'Invalid version: %s\n' "${VERSION}" >&2; exit 2; }

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
VALUES="${VALUES:-/tmp/openmaster-k3s-runpod.yaml}"
REGISTRY="${REGISTRY:-harbor.lucaslamy.fr/private/openmaster}"
NAMESPACE="${NAMESPACE:-openmaster}"
RELEASE="${RELEASE:-openmaster}"
SECRET_NAME="${SECRET_NAME:-openmaster-secrets}"
TIMEOUT="${TIMEOUT:-20m}"

for required in python3 helm kubectl; do
  command -v "${required}" >/dev/null ||
    { printf 'Missing required command: %s\n' "${required}" >&2; exit 1; }
done
[[ -f "${VALUES}" ]] || { printf 'Values file not found: %s\n' "${VALUES}" >&2; exit 1; }

backup="${VALUES}.bak.$(date -u +%Y%m%dT%H%M%SZ)"
cp -- "${VALUES}" "${backup}"

python3 "${ROOT_DIR}/deployment/scripts/update-runpod-values.py" \
  "${VALUES}" "${VERSION}" "${REGISTRY}"

printf 'Updated %s; backup: %s\n' "${VALUES}" "${backup}"
export VALUES NAMESPACE RELEASE SECRET_NAME TIMEOUT
"${ROOT_DIR}/deployment/scripts/deploy.sh"

printf 'Deployed OpenMaster %s to %s/%s\n' "${VERSION}" "${NAMESPACE}" "${RELEASE}"
