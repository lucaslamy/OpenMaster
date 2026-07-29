# Déployer OpenMaster 3.6.0

Cette release ajoute les comptes privés, les sessions révocables, l’approbation des
inscriptions par un administrateur et la migration Alembic `0012`.

## 1. Préparer les secrets avant le déploiement

L’API 3.6.0 ne démarre pas sans un compte administrateur initial. Ajoutez ces deux clés
au même chemin Vault que `openmaster-secrets` :

```bash
read -rp "E-mail administrateur OpenMaster : " OPENMASTER_ADMIN_EMAIL
read -rsp "Mot de passe administrateur OpenMaster : " OPENMASTER_ADMIN_PASSWORD
echo
printf '%s' "${OPENMASTER_ADMIN_EMAIL}" \
  | vault kv patch -mount=secret openmaster OPENMASTER_ADMIN_EMAIL=-
printf '%s' "${OPENMASTER_ADMIN_PASSWORD}" \
  | vault kv patch -mount=secret openmaster OPENMASTER_ADMIN_PASSWORD=-
unset OPENMASTER_ADMIN_EMAIL OPENMASTER_ADMIN_PASSWORD
```

Le mot de passe doit contenir entre 10 et 128 caractères. Ne l’ajoutez ni au dépôt ni
au fichier de valeurs Helm.

Forcez ensuite la resynchronisation External Secrets selon votre installation, puis
vérifiez uniquement la présence des clés :

```bash
kubectl get secret openmaster-secrets -n openmaster \
  -o jsonpath='{.data.OPENMASTER_ADMIN_EMAIL}' | grep -q . &&
kubectl get secret openmaster-secrets -n openmaster \
  -o jsonpath='{.data.OPENMASTER_ADMIN_PASSWORD}' | grep -q . &&
echo "Secrets administrateur présents"
```

## 2. Publier les images

Depuis la machine de développement :

```bash
cd /home/eliott/Documents/OpenMaster
docker login harbor.lucaslamy.fr

REGISTRY=harbor.lucaslamy.fr/private/openmaster \
RUNPOD_REGISTRY=harbor.lucaslamy.fr/library/openmaster-runpod \
  deployment/scripts/sync-build-push.sh 3.6.0 all
```

Les images attendues sont :

```text
harbor.lucaslamy.fr/private/openmaster/api:3.6.0
harbor.lucaslamy.fr/private/openmaster/web:3.6.0
harbor.lucaslamy.fr/library/openmaster-runpod:3.6.0
```

## 3. Déployer sur k3s

Sur le serveur k3s, avec le dépôt synchronisé :

```bash
cd /root/openmaster

export VALUES=/tmp/openmaster-k3s-runpod.yaml
export REGISTRY=harbor.lucaslamy.fr/private/openmaster
export NAMESPACE=openmaster
export RELEASE=openmaster
export SECRET_NAME=openmaster-secrets
export TIMEOUT=20m

deployment/scripts/deploy-runpod-version.sh 3.6.0
```

Le script sauvegarde le fichier de valeurs, épingle API, Web et workers, exécute le
préflight, puis lance un `helm upgrade --install --atomic`. Le hook de migration doit
appliquer `0012` avant le démarrage des nouveaux pods.

## 4. Vérifier la migration et le rollout

```bash
kubectl get jobs,pods -n openmaster
kubectl logs -n openmaster -l app.kubernetes.io/component=migration --tail=200
kubectl rollout status deployment/openmaster-openmaster-api -n openmaster --timeout=10m
kubectl rollout status deployment/openmaster-openmaster-web -n openmaster --timeout=10m
```

Vérifiez la version Alembic :

```bash
kubectl exec -n openmaster deployment/openmaster-openmaster-api -- \
  python -m alembic current
```

Le résultat attendu est `0012 (head)`.

## 5. Vérifier l’administrateur et les inscriptions

Ouvrez le site, connectez-vous avec `OPENMASTER_ADMIN_EMAIL`, puis ouvrez l’entrée
**Admin** dans la navigation. Dans une fenêtre privée :

1. créez une demande de compte ;
2. confirmez qu’aucune session n’est ouverte ;
3. validez la demande depuis le compte administrateur ;
4. connectez-vous avec le nouveau compte ;
5. confirmez que son historique de projets est vide et privé.

Contrôle API optionnel sans afficher le cookie :

```bash
read -rp "E-mail administrateur : " ADMIN_EMAIL
read -rsp "Mot de passe administrateur : " ADMIN_PASSWORD
echo
printf '{"email":"%s","password":"%s"}' "${ADMIN_EMAIL}" "${ADMIN_PASSWORD}" \
  | curl -fsS -c /tmp/openmaster-admin.cookies \
      -H 'Content-Type: application/json' \
      --data-binary @- \
      https://openmaster.lucaslamy.fr/api/v1/auth/login
unset ADMIN_EMAIL ADMIN_PASSWORD

curl -fsS -b /tmp/openmaster-admin.cookies \
  https://openmaster.lucaslamy.fr/api/v1/auth/admin/requests
```

Supprimez ensuite `/tmp/openmaster-admin.cookies`.

## 6. Projets antérieurs

Les projets créés avant `0012` sont conservés dans PostgreSQL et MinIO mais restent
sans propriétaire. Ils ne sont visibles par aucun compte afin d’éviter une attribution
accidentelle. Ne modifiez pas leur schéma manuellement ; une procédure d’attribution
explicite devra être utilisée si leur récupération est nécessaire.

## 7. Retour arrière

Le rollback applicatif ne nécessite pas de supprimer les nouvelles tables :

```bash
helm history openmaster -n openmaster
deployment/scripts/rollback.sh REVISION_PRECEDENTE
```

Les colonnes et tables supplémentaires sont ignorées par la version précédente. Ne
lancez `alembic downgrade 0011` qu’après sauvegarde et uniquement si les comptes et
sessions 3.6.0 doivent réellement être supprimés.
