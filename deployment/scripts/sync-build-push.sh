#!/usr/bin/env bash
# Synchronize OpenMaster to the build host, then build and push selected images.

set -Eeuo pipefail

usage() {
  cat <<'EOF'
Usage: deployment/scripts/sync-build-push.sh VERSION COMPONENT [COMPONENT...]

Components: api, web, runpod, all

Examples:
  deployment/scripts/sync-build-push.sh 3.6.1 api web
  deployment/scripts/sync-build-push.sh 3.6.1 runpod
  deployment/scripts/sync-build-push.sh 3.6.1 all

Optional environment:
  SOURCE_DIR, SSH_KEY, REMOTE, REMOTE_DIR, REGISTRY, RUNPOD_REGISTRY, SKIP_SYNC=1

Image repositories:
  api/web: ${REGISTRY}/COMPONENT:VERSION
  runpod:  ${RUNPOD_REGISTRY}:VERSION
EOF
}

[[ $# -ge 2 ]] || { usage >&2; exit 2; }
VERSION="$1"
shift
[[ "${VERSION}" =~ ^[0-9]+\.[0-9]+\.[0-9]+([.-][0-9A-Za-z.-]+)?$ ]] ||
  { printf 'Invalid version: %s\n' "${VERSION}" >&2; exit 2; }

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
SOURCE_DIR="${SOURCE_DIR:-${ROOT_DIR}}"
SSH_KEY="${SSH_KEY:-/home/eliott/.ssh/id_rsa}"
REMOTE="${REMOTE:-root@46.225.231.203}"
REMOTE_DIR="${REMOTE_DIR:-/root/openmaster/}"
REGISTRY="${REGISTRY:-harbor.lucaslamy.fr/private/openmaster}"
RUNPOD_REGISTRY="${RUNPOD_REGISTRY:-harbor.lucaslamy.fr/library/openmaster-runpod}"
REGISTRY="${REGISTRY%/}"
RUNPOD_REGISTRY="${RUNPOD_REGISTRY%/}"

declare -a COMPONENTS=()
for requested in "$@"; do
  case "${requested}" in
    all) COMPONENTS=(api web runpod); break ;;
    api|web|runpod) COMPONENTS+=("${requested}") ;;
    *) printf 'Unknown component: %s\n' "${requested}" >&2; usage >&2; exit 2 ;;
  esac
done

for required in rsync ssh docker; do
  command -v "${required}" >/dev/null ||
    { printf 'Missing required command: %s\n' "${required}" >&2; exit 1; }
done
[[ -d "${SOURCE_DIR}" ]] || { printf 'Source directory not found: %s\n' "${SOURCE_DIR}" >&2; exit 1; }
[[ -r "${SSH_KEY}" ]] || { printf 'SSH key is not readable: %s\n' "${SSH_KEY}" >&2; exit 1; }

if [[ "${SKIP_SYNC:-0}" != "1" ]]; then
  printf -v remote_dir_quoted '%q' "${REMOTE_DIR}"
  ssh -i "${SSH_KEY}" "${REMOTE}" "mkdir -p -- ${remote_dir_quoted}"
  rsync -avz --progress \
    --exclude '.git/' \
    --exclude '.env' \
    --exclude 'node_modules/' \
    --exclude '__pycache__/' \
    -e "ssh -i ${SSH_KEY}" \
    "${SOURCE_DIR}/" "${REMOTE}:${REMOTE_DIR}"
fi

for component in "${COMPONENTS[@]}"; do
  dockerfile="Dockerfile.${component}"
  if [[ "${component}" == "runpod" ]]; then
    image="${RUNPOD_REGISTRY}:${VERSION}"
  else
    image="${REGISTRY}/${component}:${VERSION}"
  fi
  printf 'Building and pushing %s\n' "${image}"
  docker buildx build --push -f "${ROOT_DIR}/${dockerfile}" -t "${image}" "${ROOT_DIR}"
done

printf 'Published version %s (%s)\n' "${VERSION}" "${COMPONENTS[*]}"
