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
La conservation des projets et la décision pré-master `3.1.0` sont documentées dans
[`docs/PROJECT_HISTORY.md`](../docs/PROJECT_HISTORY.md).
Les comptes privés et l’approbation administrateur `3.6.0` disposent d’un
[runbook de déploiement dédié](../docs/deployment/release-3.6.0.fr.md).
Le correctif visuel des titres de réglages `3.6.1` dispose également d’un
[runbook de déploiement dédié](../docs/deployment/release-3.6.1.fr.md).

## Synchronisation, publication et déploiement versionné

Synchroniser le dépôt vers `root@46.225.231.203`, puis construire et publier une
sélection d'images :

```bash
deployment/scripts/sync-build-push.sh 3.6.1 api web
deployment/scripts/sync-build-push.sh 3.6.1 runpod
# ou les trois :
deployment/scripts/sync-build-push.sh 3.6.1 all
```

Le script exclut `.git`, `.env`, `node_modules` et les caches Python. Les valeurs par
défaut reproduisent la clé SSH et le serveur de production. API et Web sont publiés
sous `harbor.lucaslamy.fr/private/openmaster/{api,web}:VERSION`, tandis que le worker
RunPod utilise son dépôt distinct
`harbor.lucaslamy.fr/library/openmaster-runpod:VERSION`. Les racines restent
surchargeables avec `REGISTRY` et `RUNPOD_REGISTRY`. `SKIP_SYNC=1` permet de
republier sans relancer rsync.

Exemple explicite :

```bash
REGISTRY=harbor.lucaslamy.fr/private/openmaster \
RUNPOD_REGISTRY=harbor.lucaslamy.fr/library/openmaster-runpod \
  deployment/scripts/sync-build-push.sh 3.6.1 all
```

Sur le serveur k3s, épingler la version dans le fichier RunPod puis lancer le
préflight et le déploiement Helm atomique :

```bash
deployment/scripts/deploy-runpod-version.sh 3.6.1
```

Le fichier par défaut est `/tmp/openmaster-k3s-runpod.yaml`. Une sauvegarde horodatée
est créée avant modification. Aucun parseur YAML externe n'est nécessaire.
