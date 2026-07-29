# Déployer OpenMaster 3.6.1

OpenMaster `3.6.1` est un correctif visuel ciblé : tous les titres des réglages de
mastering utilisent désormais la même structure `legend.control-heading`, avec un
séparateur interne uniquement dans les blocs qui regroupent plusieurs réglages.

Cette version n’ajoute aucune migration de base de données ni aucun secret. Elle
conserve le schéma Alembic et les variables d’administration introduits par `3.6.0`.
Le DSP et l’image RunPod ne changent pas.

## 1. Vérifier les secrets existants

Le secret `openmaster-secrets` doit toujours contenir les identifiants du compte
administrateur initial :

```bash
kubectl get secret openmaster-secrets -n openmaster \
  -o jsonpath='{.data.OPENMASTER_ADMIN_EMAIL}' | base64 -d
echo
kubectl get secret openmaster-secrets -n openmaster \
  -o jsonpath='{.data.OPENMASTER_ADMIN_PASSWORD}' | base64 -d | wc -c
```

La seconde commande n’affiche que la longueur du mot de passe, pas sa valeur.

## 2. Construire et publier API et Web

Depuis la machine de développement :

```bash
cd /home/eliott/Documents/OpenMaster
export VERSION=3.6.1
docker login harbor.lucaslamy.fr
deployment/scripts/sync-build-push.sh "${VERSION}" api web
```

Le script synchronise le dépôt vers le serveur configuré, puis publie :

```text
harbor.lucaslamy.fr/private/openmaster/api:3.6.1
harbor.lucaslamy.fr/private/openmaster/web:3.6.1
```

L’image `harbor.lucaslamy.fr/library/openmaster-runpod:3.6.0` peut rester déployée :
le moteur DSP n’a pas changé. Il est inutile de reconstruire RunPod pour ce correctif.

## 3. Déployer sur k3s

Depuis le serveur Kubernetes :

```bash
cd /root/openmaster
export VERSION=3.6.1
export REGISTRY=harbor.lucaslamy.fr/private/openmaster
export NAMESPACE=openmaster
export RELEASE=openmaster
export VALUES=/tmp/openmaster-k3s-runpod.yaml
export SECRET_NAME=openmaster-secrets
export TIMEOUT=20m
deployment/scripts/deploy-runpod-version.sh "${VERSION}"
```

Le script sauvegarde le fichier de valeurs, remplace les tags API/Web par `3.6.1`,
préserve le dépôt RunPod distinct, exécute les contrôles préalables puis lance la mise
à niveau Helm.

## 4. Vérifier le déploiement

```bash
kubectl get pods -n openmaster
kubectl get deployment -n openmaster \
  -o custom-columns='NAME:.metadata.name,IMAGE:.spec.template.spec.containers[*].image'
kubectl rollout status deployment/openmaster-openmaster-api \
  -n openmaster --timeout=10m
kubectl rollout status deployment/openmaster-openmaster-web \
  -n openmaster --timeout=10m
curl -fsS https://openmaster.lucaslamy.fr/api/health
```

Dans le navigateur, vider au besoin le cache, ouvrir les réglages de mastering et
vérifier que :

- tous les titres de sections ont la même typographie et restent dans leur carte ;
- les blocs à plusieurs réglages ont un séparateur horizontal ;
- les cartes à réglage unique n’affichent pas de séparateur superflu ;
- l’inscription, la connexion et l’approbation administrateur fonctionnent toujours.

## 5. Revenir à la révision précédente

La version ne modifiant pas le schéma SQL, aucun downgrade Alembic n’est nécessaire :

```bash
helm history openmaster -n openmaster
helm rollback openmaster <revision> -n openmaster --wait --timeout 20m
```
