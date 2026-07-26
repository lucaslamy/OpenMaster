# OpenMaster deployment operations

The scripts target an existing Kubernetes or k3s cluster and never create secret
values. Label the namespace for the `ClusterExternalSecret`, wait for
`openmaster-secrets`, then run:

```bash
NAMESPACE=openmaster VALUES=helm/openmaster/values-production.yaml \
  deployment/scripts/preflight-check.sh
deployment/scripts/deploy.sh
deployment/scripts/smoke-test.sh
deployment/scripts/rollback.sh [revision]
```

All parameters can be overridden with `RELEASE`, `NAMESPACE`, `CHART`, `VALUES`,
`SECRET_NAME`, and `TIMEOUT`. The deploy is atomic: a failed migration, readiness
probe, or rollout causes Helm to restore the previous release.

Un guide k3s complet en français est disponible dans
[`docs/deployment/k3s-quickstart.fr.md`](../docs/deployment/k3s-quickstart.fr.md).
Pour la mise à niveau `3.0.1`, utilisez le
[runbook de release](../docs/deployment/release-3.0.1.fr.md).
Le correctif d’autorisation instantanée `3.0.2` possède un
[runbook dédié](../docs/deployment/release-3.0.2.fr.md).
