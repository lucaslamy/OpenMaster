#!/usr/bin/env bash
set -Eeuo pipefail

NAMESPACE="${NAMESPACE:-openmaster}"
RELEASE="${RELEASE:-openmaster}"
API_SERVICE="${RELEASE}-openmaster-api"
WEB_SERVICE="${RELEASE}-openmaster-web"

kubectl get --raw \
  "/api/v1/namespaces/${NAMESPACE}/services/http:${API_SERVICE}:8000/proxy/health/live" >/dev/null
kubectl get --raw \
  "/api/v1/namespaces/${NAMESPACE}/services/http:${API_SERVICE}:8000/proxy/health/ready" >/dev/null
kubectl get --raw \
  "/api/v1/namespaces/${NAMESPACE}/services/http:${WEB_SERVICE}:80/proxy/" >/dev/null

printf 'API and web smoke tests passed in namespace %s.\n' "${NAMESPACE}"
