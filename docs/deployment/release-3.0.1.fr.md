# Déployer OpenMaster 3.0.1

Ce runbook met à niveau une installation Helm existante vers OpenMaster `3.0.1`.
La release ajoute la migration Alembic réversible `0010`, l’interface unifiée, la
pré-écoute Web Audio et les rendus finaux réutilisant la source et l’analyse.

## 1. Préparer et sauvegarder

Depuis la machine d’administration :

```bash
git fetch --tags origin
git checkout v3.0.1
kubectl config current-context
helm history openmaster -n openmaster
kubectl get pods -n openmaster
```

Sauvegardez PostgreSQL et vérifiez la restauration selon la procédure de votre
exploitant. Avec PostgreSQL interne, un exemple ponctuel est :

```bash
kubectl exec -n openmaster deployment/openmaster-openmaster-postgres -- \
  pg_dump -U openmaster -Fc openmaster > /tmp/openmaster-before-3.0.1.dump
test -s /tmp/openmaster-before-3.0.1.dump
```

Le nom d’utilisateur et de base doit correspondre à votre Secret. Ne lisez pas les
valeurs secrètes dans les logs.

## 2. Construire et publier les images

```bash
export REGISTRY=harbor.example.com/openmaster
export VERSION=3.0.1

docker build -f Dockerfile.api -t "${REGISTRY}/api:${VERSION}" .
docker build -f Dockerfile.web -t "${REGISTRY}/web:${VERSION}" .
docker push "${REGISTRY}/api:${VERSION}"
docker push "${REGISTRY}/web:${VERSION}"
```

Si RunPod est activé :

```bash
export RUNPOD_REGISTRY=harbor.lucaslamy.fr/library/openmaster-runpod
docker build --platform linux/amd64 -f Dockerfile.runpod \
  -t "${RUNPOD_REGISTRY}:${VERSION}" .
docker push "${RUNPOD_REGISTRY}:${VERSION}"
```

## 3. Mettre à jour les valeurs privées

Dans votre fichier de valeurs hors Git :

```yaml
api:
  image: harbor.example.com/openmaster/api:3.0.1
web:
  image: harbor.example.com/openmaster/web:3.0.1
workers:
  image: harbor.example.com/openmaster/api:3.0.1
```

Conservez `MASTERING_ACCESS_PASSWORD` dans `openmaster-secrets`. Aucune nouvelle
variable d’environnement n’est nécessaire pour `3.0.1`.

Vérifiez que l’Ingress transmet `/api` et permet les uploads attendus. Le fichier WAV
haute qualité est utilisé pour la pré-écoute ; prévoyez des timeouts et une taille de
requête adaptés.

## 4. Préflight et déploiement atomique

```bash
export NAMESPACE=openmaster
export RELEASE=openmaster
export VALUES=/chemin/prive/openmaster-production.yaml
export SECRET_NAME=openmaster-secrets
export TIMEOUT=15m

deployment/scripts/preflight-check.sh
deployment/scripts/deploy.sh
```

Le hook Helm applique Alembic `0010`, qui ajoute la lignée du rendu final et les
réglages interactifs. Le déploiement est `--atomic --wait` : une migration ou un
rollout en échec déclenche le rollback Helm.

## 5. Vérifications

```bash
helm status openmaster -n openmaster
kubectl get pods,job,ingress -n openmaster
deployment/scripts/smoke-test.sh
kubectl logs -n openmaster deployment/openmaster-openmaster-api --since=10m
kubectl logs -n openmaster deployment/openmaster-openmaster-mastering-worker --since=10m
```

Dans le navigateur :

1. importer un morceau ;
2. vérifier qu’un mauvais mot de passe ne crée aucun job ;
3. produire le premier master ;
4. déplacer EQ, LUFS, clipper, saturation et limiteur pendant la lecture ;
5. comparer A/B sans perte de position ;
6. enregistrer les réglages et lancer le rendu final ;
7. vérifier que le job final ne repasse pas par l’analyse.

## 6. Rollback

```bash
helm history openmaster -n openmaster
deployment/scripts/rollback.sh REVISION_PRECEDENTE
```

La migration `0010` est additive et les anciennes applications ignorent ses colonnes.
Ne lancez `alembic downgrade 0009` qu’après avoir arrêté les composants `3.0.1` et
confirmé qu’aucun rendu final ne doit être conservé. Un rollback Helm ne restaure pas
la base ni les objets MinIO.
