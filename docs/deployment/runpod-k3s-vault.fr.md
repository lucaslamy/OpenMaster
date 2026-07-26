# Runbook complet : OpenMaster avec RunPod, k3s et Vault

Ce guide décrit, dans l’ordre, toutes les opérations nécessaires pour conserver le plan
de contrôle OpenMaster sur un petit cluster k3s et déléguer les traitements audio lourds
à RunPod Serverless.

## Architecture finale

```text
Utilisateur
    |
    v
OpenMaster sur k3s
API + petits workers + Redis + PostgreSQL
    |
    | tâche distante + URLs HTTPS temporaires
    v
RunPod Serverless CPU
analyse + mastering + export
    |
    v
Stockage objet accessible en HTTPS
```

k3s reste allumé avec de faibles ressources. RunPod démarre uniquement lorsqu’un
morceau doit être traité.

> Important : l’image RunPod actuelle utilise Python 3.12 et le CPU. Elle ne contient
> pas encore de backend IA CUDA. Commencez avec un endpoint RunPod CPU. Louer une GPU
> avant l’intégration d’un modèle PyTorch, ONNX ou CuPy compatible coûterait plus cher
> sans accélération garantie.

## 1. Mettre OpenMaster à jour

Sur le serveur k3s :

```bash
cd /root/openmaster
git pull
git log -3 --oneline
```

La version doit contenir au minimum :

```text
a57a384 feat(compute): add optional RunPod processing boundary
26b3b99 fix(helm): run initial migration after data services
```

Vérifiez les fichiers :

```bash
test -f Dockerfile.runpod
test -f docs/deployment/runpod.md
test -f deployment/examples/values-runpod.example.yaml
```

## 2. Publier l’API S3 du MinIO interne

RunPod ne peut pas accéder à une adresse interne Kubernetes comme :

```text
openmaster-openmaster-minio.openmaster.svc.cluster.local
```

Le chart peut publier le port API du MinIO déjà déployé dans k3s. Le worker distant
utilise son interface S3 et reçoit :

- une URL GET HTTPS présignée pour télécharger la source ;
- une URL PUT HTTPS présignée pour envoyer le master.

Réservez un sous-domaine, par exemple :

```text
https://s3.example.com
```

Créez son enregistrement DNS vers l’adresse publique de Traefik. Le chart crée un
Ingress TLS vers le port API `9000` et complète la NetworkPolicy MinIO pour autoriser
Traefik. La console MinIO, servie séparément, ne reçoit aucune route Ingress. Le port
API contient aussi des chemins administratifs MinIO protégés par authentification ;
limitez l’exposition au domaine TLS prévu et ne diffusez jamais les identifiants root.

Le bucket reste privé. L’API S3 exige une signature AWS v4 ; RunPod ne reçoit que des
URLs GET/PUT présignées à courte durée. MinIO recommande des hôtes distincts pour l’API
S3 et la console derrière un Ingress :
[documentation MinIO](https://docs.min.io/aistor/installation/kubernetes/load-balancing/).

## 3. Construire et publier l’image RunPod

Choisissez un registre accessible par RunPod : Docker Hub, GitHub Container Registry ou
un registre privé configuré dans RunPod.

```bash
cd /root/openmaster

export REGISTRY=docker.io/REPLACE_WITH_ACCOUNT
export VERSION=2.8.0

docker login
```

Construisez l’image AMD64 :

```bash
docker build \
  --platform linux/amd64 \
  -f Dockerfile.runpod \
  -t "${REGISTRY}/openmaster-runpod:${VERSION}" \
  .
```

Vérifiez son démarrage :

```bash
docker run --rm \
  -e OPENMASTER_ALLOWED_STORAGE_HOSTS=s3.example.com \
  -e OPENMASTER_MAX_REMOTE_BYTES=268435456 \
  "${REGISTRY}/openmaster-runpod:${VERSION}"
```

Le conteneur attend l’environnement RunPod. Interrompez le test avec `Ctrl+C`, puis
publiez l’image :

```bash
docker push "${REGISTRY}/openmaster-runpod:${VERSION}"
```

## 4. Créer une clé API RunPod

Dans l’interface RunPod :

1. ouvrez les paramètres du compte ;
2. ouvrez la gestion des clés API ;
3. créez une clé dédiée à OpenMaster ;
4. copiez-la immédiatement ;
5. ne la placez jamais dans Git ou dans les valeurs Helm.

La clé sera ensuite enregistrée dans Vault.

## 5. Créer l’endpoint RunPod Serverless

Dans RunPod :

1. ouvrez **Serverless** ;
2. cliquez sur **New Endpoint** ;
3. choisissez un endpoint **Queue-based** ;
4. sélectionnez votre image Docker ;
5. choisissez un endpoint **CPU** pour commencer.

Configuration initiale recommandée :

| Paramètre | Valeur |
| --- | ---: |
| Type | Queue-based |
| Compute | CPU |
| vCPU | 2 ou 4 |
| Active/min workers | 0 |
| Max workers | 1 |
| Idle timeout | 5 à 15 secondes |
| Execution timeout | 3 600 secondes |
| FlashBoot | Activé |
| Scaling | Queue delay |
| Queue delay | 4 secondes |

Avec zéro worker actif, RunPod revient à zéro au repos. Le premier job subit alors un
cold start.

Documentation officielle :

- [création d’un endpoint](https://docs.runpod.io/api-reference/endpoints/POST/endpoints) ;
- [fonctionnement Serverless](https://docs.runpod.io/serverless/overview) ;
- [configuration des endpoints](https://docs.runpod.io/serverless/endpoints/endpoint-configurations).

### Variables du worker RunPod

Ajoutez dans l’endpoint :

```text
OPENMASTER_ALLOWED_STORAGE_HOSTS=s3.example.com
OPENMASTER_MAX_REMOTE_BYTES=268435456
```

Pour plusieurs hôtes :

```text
OPENMASTER_ALLOWED_STORAGE_HOSTS=s3.example.com,storage.example.net
```

Utilisez uniquement les noms d’hôtes, sans `https://` ni chemin. La limite
`268435456` correspond à 256 Mio.

Après la création, conservez l’identifiant :

```text
RUNPOD_ENDPOINT_ID=REPLACE_WITH_ENDPOINT_ID
```

## 6. Vérifier l’endpoint RunPod

Depuis le serveur :

```bash
export RUNPOD_ENDPOINT_ID=REPLACE_WITH_ENDPOINT_ID
read -rsp "Clé API RunPod : " RUNPOD_API_KEY
echo
```

Testez la santé :

```bash
curl -fsS \
  -H "Authorization: Bearer ${RUNPOD_API_KEY}" \
  "https://api.runpod.ai/v2/${RUNPOD_ENDPOINT_ID}/health"
```

## 7. Ajouter la clé RunPod dans Vault

Les commandes suivantes supposent un moteur KV v2 monté sous `secret/` et le secret
OpenMaster sous `openmaster`.

Si la variable n’est plus définie :

```bash
read -rsp "Clé API RunPod : " RUNPOD_API_KEY
echo
```

Ajoutez uniquement cette clé sans écraser les autres :

```bash
printf '%s' "${RUNPOD_API_KEY}" \
  | vault kv patch \
      -mount=secret \
      openmaster \
      RUNPOD_API_KEY=-
```

Vault accepte `-` pour lire une valeur depuis l’entrée standard :
[documentation Vault CLI](https://developer.hashicorp.com/vault/docs/commands) et
[KV patch](https://developer.hashicorp.com/vault/docs/secrets/kv/kv-v2/cookbook/patch-data).

Effacez la variable locale :

```bash
unset RUNPOD_API_KEY
```

Ajoutez également le mot de passe demandé avant chaque nouveau mastering :

```bash
read -rsp "Mot de passe du studio OpenMaster : " MASTERING_ACCESS_PASSWORD
echo
printf '%s' "${MASTERING_ACCESS_PASSWORD}" \
  | vault kv patch \
      -mount=secret \
      openmaster \
      MASTERING_ACCESS_PASSWORD=-
unset MASTERING_ACCESS_PASSWORD
```

## 8. Synchroniser le Secret Kubernetes

Forcez External Secrets à relire Vault :

```bash
kubectl annotate externalsecret openmaster \
  -n openmaster \
  force-sync="$(date +%s)" \
  --overwrite
```

Attendez l’état prêt :

```bash
kubectl get externalsecret openmaster -n openmaster -w
```

Vérifiez la présence de la clé sans l’afficher :

```bash
kubectl get secret openmaster-secrets \
  -n openmaster \
  -o 'jsonpath={.data.RUNPOD_API_KEY}' \
  | grep -q . \
  && echo "RUNPOD_API_KEY présente"
```

Le Secret doit contenir au moins :

```text
DATABASE_URL
CELERY_BROKER_URL
CELERY_RESULT_BACKEND
POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD
MINIO_ROOT_USER
MINIO_ROOT_PASSWORD
RUNPOD_API_KEY
MASTERING_ACCESS_PASSWORD
```

## 9. Préparer les valeurs k3s

Partez de la configuration minimale déjà adaptée à votre cluster :

```bash
cp /tmp/openmaster-k3s-minimal.yaml \
   /tmp/openmaster-k3s-runpod.yaml
```

Ajoutez ou remplacez :

```yaml
remoteCompute:
  enabled: true
  provider: runpod
  endpointId: REPLACE_WITH_RUNPOD_ENDPOINT_ID
  egressCIDRs:
    - 0.0.0.0/0

minio:
  enabled: true
  bucket: openmaster
  region: us-east-1
  publicIngress:
    enabled: true
    className: traefik
    host: s3.example.com
    publicEndpoint: https://s3.example.com
    tls:
      enabled: true
      secretName: openmaster-minio-tls

ingress:
  enabled: true
  className: nginx
  controllerNamespace: ingress-nginx
  controllerPodLabels:
    app.kubernetes.io/name: ingress-nginx
    app.kubernetes.io/component: controller
  annotations:
    nginx.ingress.kubernetes.io/proxy-body-size: "2048m"
  host: openmaster.example.com
  tls:
    enabled: true
    secretName: openmaster-tls

workers:
  mastering:
    replicaCount: 1
    concurrency: 1
    resources:
      requests:
        cpu: 50m
        memory: 128Mi
      limits:
        cpu: 250m
        memory: 256Mi

autoscaling:
  enabled: false

podDisruptionBudget:
  enabled: false
```

L’annotation `proxy-body-size` doit rester cohérente avec `MAX_UPLOAD_BYTES`. Sans
elle, ingress-nginx peut rejeter un MP3 avant que l’API ne puisse produire une réponse
JSON. Le workflow web utilise `POST /api/v1/analysis-jobs`, stocke la source dans le
bucket `openmaster`, puis interroge `GET /api/v1/analysis-jobs/{id}` pendant le
traitement Celery.

### Réutiliser le MinIO de ClipForge

Un seul serveur MinIO peut servir ClipForge et OpenMaster sans mélanger leurs
fichiers. Utilisez un bucket `clipforge` pour ClipForge et un bucket `openmaster`
pour OpenMaster.

Le manifeste corrigé se trouve dans
[`deployment/examples/minio-shared-clipforge-openmaster.yaml`](../../deployment/examples/minio-shared-clipforge-openmaster.yaml).
Il conserve MinIO dans le namespace `clipforge`, expose uniquement son API avec TLS
et laisse la console privée.

Configurez OpenMaster ainsi :

```yaml
minio:
  enabled: false
  externalHost: minio.clipforge.svc.cluster.local
  externalPort: 9000
  externalPublicEndpoint: https://s3.example.com
  bucket: openmaster
  region: us-east-1
  externalNetworkPolicy:
    namespaceSelector:
      kubernetes.io/metadata.name: clipforge
    podSelector:
      app: minio
```

Créez le bucket dédié :

```bash
mc alias set shared-minio https://s3.example.com "$MINIO_USER" "$MINIO_PASSWORD"
mc mb --ignore-existing shared-minio/openmaster
```

Les identifiants existants fonctionneront s’ils sont copiés dans Vault sous
`MINIO_ROOT_USER` et `MINIO_ROOT_PASSWORD`. En production, créez plutôt une access
key propre à OpenMaster, limitée au bucket `openmaster`, puis stockez-la sous ces
deux noms historiques de variables.

Comme l’Ingress partagé est dans `clipforge`, son certificat doit être dans le même
namespace :

```bash
kubectl create secret tls shared-minio-tls \
  -n clipforge \
  --cert=/path/to/fullchain.pem \
  --key=/path/to/privkey.pem
```

La règle `0.0.0.0/0` est limitée au worker mastering, à TCP et au port `443`. Elle est
nécessaire avec une NetworkPolicy standard lorsque les IP de RunPod ne sont pas stables.
Pour une restriction par domaine, utilisez un proxy egress ou un CNI supportant les
politiques FQDN.

Conservez également les images normales de k3s :

```yaml
api:
  image: REPLACE_WITH_REGISTRY/openmaster-api:2.8.0

web:
  image: REPLACE_WITH_REGISTRY/openmaster-web:2.8.0

workers:
  image: REPLACE_WITH_REGISTRY/openmaster-api:2.8.0
```

L’image `openmaster-runpod` est configurée dans RunPod uniquement, pas dans Helm.

Créez le Secret TLS avant le déploiement si cert-manager ne le gère pas :

```bash
kubectl create secret tls openmaster-minio-tls \
  -n openmaster \
  --cert=/path/to/fullchain.pem \
  --key=/path/to/privkey.pem
```

Le certificat doit couvrir exactement `s3.example.com`. N’utilisez pas de certificat
autosigné : RunPod doit pouvoir valider toute la chaîne TLS.

## 10. Valider Helm et les secrets

```bash
cd /root/openmaster

export NAMESPACE=openmaster
export RELEASE=openmaster
export VALUES=/tmp/openmaster-k3s-runpod.yaml
export SECRET_NAME=openmaster-secrets

deployment/scripts/preflight-check.sh
```

Le préflight vérifie aussi `RUNPOD_API_KEY` lorsque le calcul distant est activé.

Contrôlez le rendu :

```bash
helm template openmaster helm/openmaster \
  --namespace openmaster \
  -f helm/openmaster/values.yaml \
  -f /tmp/openmaster-k3s-runpod.yaml \
  | grep -E 'RUNPOD_ENDPOINT_ID|OPENMASTER_REMOTE_COMPUTE_ENABLED'
```

Résultat attendu :

```text
OPENMASTER_REMOTE_COMPUTE_ENABLED: "true"
RUNPOD_ENDPOINT_ID: "votre-endpoint"
```

## 11. Déployer sur k3s

Pour le premier essai, n’utilisez pas `--atomic`, afin de conserver les ressources en
cas d’échec :

```bash
helm upgrade --install openmaster helm/openmaster \
  --namespace openmaster \
  --create-namespace \
  -f helm/openmaster/values.yaml \
  -f /tmp/openmaster-k3s-runpod.yaml \
  --wait \
  --timeout 20m
```

Dans un autre terminal :

```bash
watch kubectl get pods,pvc,jobs -n openmaster
```

Tous les Pods doivent devenir `Running` et le Job Alembic `Completed`.

Vérifiez l’Ingress S3 et la santé publique de MinIO :

```bash
kubectl get ingress openmaster-openmaster-minio -n openmaster
curl -fsS https://s3.example.com/minio/health/live
curl -fsS https://s3.example.com/minio/health/ready
```

Vérifiez la configuration non secrète du worker :

```bash
kubectl exec -n openmaster \
  deployment/openmaster-openmaster-mastering-worker \
  -- printenv OPENMASTER_REMOTE_COMPUTE_ENABLED

kubectl exec -n openmaster \
  deployment/openmaster-openmaster-mastering-worker \
  -- printenv RUNPOD_ENDPOINT_ID
```

N’affichez jamais `RUNPOD_API_KEY` avec `printenv`.

## 12. Préparer un test audio manuel

Le workflow web ne génère pas encore les URLs présignées automatiquement. Le premier
test doit être manuel.

Configurez `mc` directement sur le MinIO k3s publié par le chart :

```bash
mc alias set remote \
  https://s3.example.com \
  REPLACE_WITH_ACCESS_KEY \
  REPLACE_WITH_SECRET_KEY
```

Cette commande peut entrer dans l’historique du shell. Préférez une configuration `mc`
protégée et supprimez toute ligne sensible de l’historique.

Créez un bucket privé et chargez une source :

```bash
mc mb --ignore-existing remote/openmaster
mc cp mix.wav remote/openmaster/input/test.wav
```

Calculez le SHA-256 :

```bash
SOURCE_SHA256="$(sha256sum mix.wav | awk '{print $1}')"
```

Créez les URLs temporaires :

```bash
mc share download \
  --expire 2h \
  remote/openmaster/input/test.wav

mc share upload \
  --expire 2h \
  remote/openmaster/output/test-master.wav
```

`mc share download` crée une URL GET et `mc share upload` une autorisation temporaire
d’envoi : [documentation MinIO](https://docs.min.io/aistor/reference/cli/mc-share/).

Copiez les deux URLs sans les mettre directement dans l’historique :

```bash
read -r SOURCE_URL
read -r DESTINATION_URL
export SOURCE_URL DESTINATION_URL SOURCE_SHA256
```

Vérifiez le nom d’hôte :

```bash
python -c 'import os,urllib.parse; print(urllib.parse.urlsplit(os.environ["SOURCE_URL"]).hostname)'
```

Il doit correspondre exactement à `OPENMASTER_ALLOWED_STORAGE_HOSTS`.

## 13. Envoyer un premier job RunPod

Créez un payload temporaire protégé :

```bash
umask 077

jq -n \
  --arg source_url "${SOURCE_URL}" \
  --arg destination_url "${DESTINATION_URL}" \
  --arg source_sha256 "${SOURCE_SHA256}" \
  '{
    input: {
      source_url: $source_url,
      destination_url: $destination_url,
      source_sha256: $source_sha256,
      target_lufs: -14.0,
      maximum_gain_adjustment_db: 12.0,
      ceiling_dbfs: -1.0,
      bit_depth: 24
    },
    policy: {
      executionTimeout: 3600000,
      ttl: 7200000
    }
  }' >/tmp/openmaster-runpod-job.json
```

Envoyez le job :

```bash
read -rsp "Clé API RunPod : " RUNPOD_API_KEY
echo

RESPONSE="$(
  curl -fsS \
    -X POST \
    -H "Authorization: Bearer ${RUNPOD_API_KEY}" \
    -H "Content-Type: application/json" \
    --data @/tmp/openmaster-runpod-job.json \
    "https://api.runpod.ai/v2/${RUNPOD_ENDPOINT_ID}/run"
)"

echo "${RESPONSE}" | jq
JOB_ID="$(echo "${RESPONSE}" | jq -r '.id')"
```

RunPod recommande `/run` pour les traitements asynchrones longs. Le statut est lu via
`/status/{job_id}` :
[documentation RunPod](https://docs.runpod.io/serverless/endpoints/send-requests).

Surveillez le statut :

```bash
watch -n 5 \
  "curl -fsS \
    -H 'Authorization: Bearer ${RUNPOD_API_KEY}' \
    'https://api.runpod.ai/v2/${RUNPOD_ENDPOINT_ID}/status/${JOB_ID}' \
    | jq"
```

États possibles :

```text
IN_QUEUE
IN_PROGRESS
COMPLETED
FAILED
CANCELLED
TIMED_OUT
```

Après le test :

```bash
rm -f /tmp/openmaster-runpod-job.json
unset RUNPOD_API_KEY SOURCE_URL DESTINATION_URL SOURCE_SHA256
```

## 14. Vérifier le master produit

Lorsque le job est `COMPLETED` :

```bash
mc stat remote/openmaster/output/test-master.wav
mc cp remote/openmaster/output/test-master.wav ./test-master.wav
ffprobe -hide_banner test-master.wav
sha256sum test-master.wav
```

La réponse RunPod doit contenir l’analyse, la décision, la politique, les processeurs et
le SHA-256 de la source. Le fichier WAV reste dans le stockage objet.

## 15. Passer au déploiement atomique

Une fois le test validé :

```bash
export VALUES=/tmp/openmaster-k3s-runpod.yaml
deployment/scripts/deploy.sh
```

Contrôles réguliers :

```bash
kubectl get pods,jobs,pvc -n openmaster
kubectl get externalsecret -n openmaster
kubectl logs -n openmaster \
  deployment/openmaster-openmaster-mastering-worker \
  --tail=100
```

Côté RunPod, surveillez les erreurs, la durée, les cold starts, le nombre de workers et
les dépenses.

## 16. Maîtriser les coûts

- utilisez un endpoint CPU tant qu’aucun backend GPU n’est intégré ;
- gardez `workersMin: 0` et `workersMax: 1` ;
- limitez la taille avec `OPENMASTER_MAX_REMOTE_BYTES` ;
- gardez un timeout d’exécution et un TTL bornés ;
- activez les alertes et limites de dépenses RunPod ;
- n’utilisez un volume réseau que pour mettre en cache un modèle volumineux ;
- n’activez une GPU qu’après validation d’un backend CUDA/PyTorch/ONNX réel.

## 17. État fonctionnel et limites

Fonctionnel :

- client RunPod asynchrone ;
- worker RunPod d’analyse, mastering et export ;
- Ingress TLS dédié au port API du MinIO interne, sans exposition de la console ;
- génération applicative d’URLs GET/PUT présignées avec
  `openmaster.remote_mastering_minio` ;
- validation SHA-256 ;
- URLs HTTPS signées ;
- clé RunPod gérée par Vault ;
- configuration Helm et NetworkPolicy ;
- retour à zéro des workers RunPod.

Encore manuel :

- transfert initial depuis l’interface web ;
- appel de la tâche MinIO/RunPod depuis le workflow web ;
- suivi persistant dans PostgreSQL ;
- téléchargement depuis l’interface web.

Le raccordement automatique de ces dernières étapes constitue le prochain lot
d’intégration applicative. L’infrastructure et le contrat distant peuvent déjà être
testés de bout en bout avec la procédure manuelle ci-dessus.
