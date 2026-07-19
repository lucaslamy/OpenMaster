Release target: post-v2.1

# Session handoff

The Kubernetes/Helm v2.1 delivery is complete. Add only newly discovered, reproducible
follow-up work here; enduring deployment guidance lives in `docs/deployment/`.

## Deployment follow-up

- Migrate the production ingress defaults from Traefik to NGINX Ingress when the target
  cluster standardizes on NGINX, preserving routing, TLS, upload limits, timeouts, and
  ingress-controller NetworkPolicy selectors.
