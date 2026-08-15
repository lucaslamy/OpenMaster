# Migration OpenMaster vers le nouveau cluster k3s

Ce runbook déploie OpenMaster en parallèle sur le nouveau cluster. Il ne supprime
aucune ressource de l’ancien cluster et conserve celui-ci disponible au moins 24 à 48
heures après la bascule.

## Paramètres confirmés

```bash
export OLD_CONTEXT="default"
export NEW_CONTEXT="default"
export PROJECT_NAME="openmaster"
export NAMESPACE="openmaster"
export APP_HOST="openmaster.lucaslamy.fr"
export REGISTRY="harbor.lucaslamy.fr"
export IMAGE_REPO="private/openmaster"
export TAG="3.6.1"
export STORAGE_CLASS="longhorn"
export CLUSTER_SECRET_STORE="vault-global"
export TLS_SECRET="openmaster-tls"
```

Les deux contextes peuvent porter le nom `default`, puisque les commandes sont
exécutées directement sur le serveur concerné. Sur chaque serveur, vérifiez simplement
que `default` désigne bien le cluster local avant de continuer.

## 1. Préflight read-only

Vérifiez d’abord le cluster local sur chaque serveur :

```bash
kubectl --context "${OLD_CONTEXT}" get nodes  # ancien serveur
kubectl --context "${NEW_CONTEXT}" get nodes  # nouveau serveur
```

Sur la cible, validez les prérequis sans afficher de valeurs secrètes :

```bash
kubectl --context "${NEW_CONTEXT}" top nodes
kubectl --context "${NEW_CONTEXT}" get storageclass "${STORAGE_CLASS}"
kubectl --context "${NEW_CONTEXT}" get ingressclass traefik
kubectl --context "${NEW_CONTEXT}" get clustersecretstore "${CLUSTER_SECRET_STORE}"
kubectl --context "${NEW_CONTEXT}" get secret "${TLS_SECRET}" -n "${NAMESPACE}"
getent hosts "${REGISTRY}"
```

Si le Secret TLS ou `ClusterSecretStore` n’existe pas, arrêtez-vous avant tout
déploiement. Vérifiez également la confiance TLS et la résolution de `harbor.lucaslamy.fr`
depuis chacun des nœuds k3s.

Après validation explicite de ces prérequis, préparez le namespace cible :

```bash
kubectl --context "${NEW_CONTEXT}" create namespace "${NAMESPACE}" --dry-run=client -o yaml \
  | kubectl --context "${NEW_CONTEXT}" apply -f -
kubectl --context "${NEW_CONTEXT}" label namespace "${NAMESPACE}" \
  openmaster.io/secrets=enabled --overwrite
```

Cette étape ne supprime rien ; elle prépare uniquement le namespace et son étiquette
pour External Secrets.

## 2. Inventaire et sauvegarde de l’ancien cluster

Toutes les commandes suivantes sont en lecture seule, sauf la procédure de sauvegarde
validée par l’exploitant :

```bash
export KUBE_CONTEXT="${OLD_CONTEXT}"
kubectl --context "${KUBE_CONTEXT}" get all,pvc,ingress -n "${NAMESPACE}"
kubectl --context "${KUBE_CONTEXT}" get secret -n "${NAMESPACE}"
helm --kube-context "${KUBE_CONTEXT}" list -n "${NAMESPACE}"
helm --kube-context "${KUBE_CONTEXT}" history "${PROJECT_NAME}" -n "${NAMESPACE}"
```

Avant la bascule, réalisez et testez une sauvegarde PostgreSQL ainsi qu’une copie des
objets MinIO. Préservez les identifiants d’objets et les noms de bucket. Ne copiez pas
les Secrets Kubernetes ; recréez-les via `vault-global` ou un mécanisme approuvé.

## 3. Synchronisation des secrets sur la cible

Adaptez `deployment/examples/cluster-external-secret.example.yaml` avec le chemin Vault
validé, puis vérifiez qu’il référence bien `vault-global`. Appliquez-le seulement après
validation explicite de la cible :

```bash
export KUBE_CONTEXT="${NEW_CONTEXT}"
kubectl --context "${KUBE_CONTEXT}" apply \
  -f deployment/examples/cluster-external-secret.example.yaml
kubectl --context "${KUBE_CONTEXT}" get externalsecret -n "${NAMESPACE}"
kubectl --context "${KUBE_CONTEXT}" describe secret "openmaster-secrets" -n "${NAMESPACE}"
```

`describe` permet de vérifier les métadonnées et les noms de clés sans afficher leurs
valeurs.

## 4. Déploiement parallèle

Après restauration des données et validation du Secret, exécutez les scripts directement
sur le nouveau serveur :

```bash
export KUBE_CONTEXT="${NEW_CONTEXT}"
export VALUES="helm/openmaster/values-production.yaml"

KUBE_CONTEXT="${KUBE_CONTEXT}" \
  deployment/scripts/preflight-check.sh
KUBE_CONTEXT="${KUBE_CONTEXT}" \
  deployment/scripts/deploy.sh
KUBE_CONTEXT="${KUBE_CONTEXT}" \
  deployment/scripts/smoke-test.sh
```

Le fichier de production cible les images Harbor `api`, `web` et `api` pour les
workers, utilise Traefik, `openmaster.lucaslamy.fr`, `openmaster-tls` et Longhorn.

Validez ensuite :

```bash
kubectl --context "${KUBE_CONTEXT}" get pods,svc,ingress,pvc -n "${NAMESPACE}"
helm --kube-context "${KUBE_CONTEXT}" status "${PROJECT_NAME}" -n "${NAMESPACE}"
```

## 5. Bascule et rollback

Après validation fonctionnelle complète, basculez le DNS de
`openmaster.lucaslamy.fr` vers Traefik sur le nouveau cluster. Ne supprimez rien sur
l’ancien cluster.

Rollback applicatif sur la cible :

```bash
export KUBE_CONTEXT="${NEW_CONTEXT}"
deployment/scripts/rollback.sh REVISION
```

Rollback de bascule : restaurez l’enregistrement DNS vers l’ancien cluster et conservez
les données de la cible pour analyse. Le rollback Helm ne restaure pas une migration
Alembic ; utilisez la sauvegarde PostgreSQL validée si une restauration de schéma est
nécessaire.

Surveillez les deux environnements pendant 24 à 48 heures minimum avant toute décision
de retrait de l’ancien cluster. Toute suppression ou désinstallation nécessite une
confirmation explicite séparée.
