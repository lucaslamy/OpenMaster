# OpenMaster Helm chart

The chart expects a Vault-managed Kubernetes Secret named by
`externalSecrets.existingSecretName` when external secrets are enabled. It never creates
or stores secret values. Production use starts with `values-production.yaml` and a
pre-existing `openmaster-secrets` Secret created by External Secrets Operator.
