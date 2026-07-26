# Déployer OpenMaster 3.0.2

Cette mise à jour remplace la validation du mot de passe incluse dans l’upload par une
autorisation légère préalable. Un mot de passe incorrect renvoie immédiatement `401`,
sans transfert audio ni création de traitement.

Construisez et publiez ensemble l’API et le web, car leur contrat d’autorisation doit
rester aligné :

```bash
export VERSION=3.0.2
export REGISTRY=harbor.lucaslamy.fr/private/openmaster

docker build -f Dockerfile.api -t "${REGISTRY}/api:${VERSION}" .
docker build -f Dockerfile.web -t "${REGISTRY}/web:${VERSION}" .
docker push "${REGISTRY}/api:${VERSION}"
docker push "${REGISTRY}/web:${VERSION}"
```

Utilisez les mêmes tags pour `api`, `web` et `workers`, puis :

```bash
export NAMESPACE=openmaster
export RELEASE=openmaster
export VALUES=/tmp/openmaster-k3s-runpod.yaml
export SECRET_NAME=openmaster-secrets
export TIMEOUT=20m

deployment/scripts/preflight-check.sh
deployment/scripts/deploy.sh
deployment/scripts/smoke-test.sh
```

Aucune migration ni nouvelle variable d’environnement n’est ajoutée par `3.0.2`.
`MASTERING_ACCESS_PASSWORD` doit rester un secret aléatoire long et être transmis
uniquement sous TLS.
