# Production deployment checklist

- Pin application and data-service images to reviewed immutable tags or digests.
- Use a highly available external PostgreSQL, Redis, and object store where required.
- Configure storage classes, capacity, snapshots, restore tests, and retention.
- Verify the Vault role, secret synchronization, and all required key names.
- Set the public host and TLS Secret; confirm ingress-controller NetworkPolicy labels.
- Provide narrow `networkPolicy.externalEgress` CIDRs for every external data service.
- Keep NetworkPolicies enabled and verify the CNI enforces them.
- Install metrics-server before enabling HPA.
- Keep at least two API/web replicas when PDBs are enabled.
- Run lint, render assertions, helm-unittest, shellcheck, and kubeconform.
- Run preflight, deploy, smoke tests, and record a tested rollback revision.
