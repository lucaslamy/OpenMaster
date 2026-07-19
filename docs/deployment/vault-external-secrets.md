# Vault and External Secrets

OpenMaster consumes one existing Kubernetes Secret and never renders secret data.
Install External Secrets Operator, configure a `ClusterSecretStore` named `vault`, and
adapt `deployment/examples/cluster-external-secret.example.yaml`. The resulting
`ClusterExternalSecret` creates an `ExternalSecret` in namespaces labelled
`openmaster.io/secrets=enabled`; its target must be named
`externalSecrets.existingSecretName` (by default `openmaster-secrets`).

The Vault record must expose these keys:

- `DATABASE_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`

Limit the Vault role and Kubernetes service-account binding to the deployment
namespace and path. Confirm synchronization without printing values:

```bash
kubectl describe externalsecret openmaster -n openmaster
kubectl get secret openmaster-secrets -n openmaster
```

The preflight script verifies key names and non-empty encoded entries only. Secret
rotation is handled by External Secrets; restart workloads after rotation if the
application does not reload environment variables.
