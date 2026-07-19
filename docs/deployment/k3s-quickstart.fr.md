# Déployer OpenMaster sur k3s

Ce guide déploie OpenMaster v2.1 sur un cluster k3s avec Helm. Il utilise les services
PostgreSQL, Redis et MinIO internes au chart. Pour une production à haute disponibilité,
utilisez plutôt des services managés externes et consultez la section dédiée plus bas.

Le schéma d’architecture et le parcours détaillé d’un morceau sont présentés dans
[`../PROJECT_FLOW.fr.md`](../PROJECT_FLOW.fr.md). À ce stade, le chart déploie
l’infrastructure, mais le workflow web distribué complet n’est pas encore raccordé ;
le traitement audio de bout en bout est utilisable localement en ligne de commande.

## 1. Prérequis

Depuis la machine d'administration du cluster :

```bash
kubectl version --client
helm version
kubectl get nodes
kubectl get storageclass
kubectl get ingressclass
```

Le chart nécessite Kubernetes 1.26 ou plus récent, une StorageClass fonctionnelle et
un contrôleur Ingress. Une installation k3s standard fournit généralement la
StorageClass `local-path` et Traefik.

Clonez le dépôt, puis placez-vous à sa racine :

```bash
git clone REPLACE_WITH_OPENMASTER_REPOSITORY_URL
cd OpenMaster
```

## 2. Construire et publier les images

Le registre doit être accessible par tous les nœuds k3s. Remplacez les variables
ci-dessous par votre registre et votre version :

```bash
export REGISTRY=harbor.lucaslamy.fr/private/openmaster
export VERSION=2.1.0

docker build -f Dockerfile.api -t "${REGISTRY}/api:${VERSION}" .
docker build -f Dockerfile.web -t "${REGISTRY}/web:${VERSION}" .
docker push "${REGISTRY}/api:${VERSION}"
docker push "${REGISTRY}/web:${VERSION}"
```

L'image API sert aussi aux trois workers Celery et au Job de migration Alembic.
Pour un registre privé, créez un Secret de type `docker-registry` dans le namespace et
référencez-le avec `global.imagePullSecrets` dans les valeurs Helm.

## 3. Créer le namespace

```bash
kubectl create namespace openmaster
kubectl label namespace openmaster openmaster.io/secrets=enabled --overwrite
```

Toutes les commandes suivantes supposent le namespace `openmaster` et le nom de release
Helm `openmaster`. Les noms DNS internes sont alors :

- `openmaster-openmaster-postgres:5432`
- `openmaster-openmaster-redis:6379`
- `openmaster-openmaster-minio:9000`

## 4. Fournir les secrets

### Option recommandée : Vault et External Secrets

Installez External Secrets Operator, configurez un `ClusterSecretStore` nommé `vault`,
puis adaptez et appliquez l'exemple :

```bash
cp deployment/examples/cluster-external-secret.example.yaml /tmp/openmaster-external-secret.yaml
# Remplacer REPLACE_WITH_VAULT_PATH dans le fichier.
kubectl apply -f /tmp/openmaster-external-secret.yaml
kubectl get externalsecret -n openmaster
kubectl get secret openmaster-secrets -n openmaster
```

Le chemin Vault doit contenir les clés suivantes :

```text
DATABASE_URL
CELERY_BROKER_URL
CELERY_RESULT_BACKEND
POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD
MINIO_ROOT_USER
MINIO_ROOT_PASSWORD
```

Avec les services internes, les trois URL ont typiquement cette forme :

```text
DATABASE_URL=postgresql+psycopg://openmaster:MOT_DE_PASSE@openmaster-openmaster-postgres:5432/openmaster
CELERY_BROKER_URL=redis://openmaster-openmaster-redis:6379/0
CELERY_RESULT_BACKEND=redis://openmaster-openmaster-redis:6379/1
```

Ne placez aucune valeur secrète dans Git ou dans un fichier de valeurs Helm. Le guide
complet Vault se trouve dans
[`vault-external-secrets.md`](vault-external-secrets.md).

### Option de démarrage sans Vault

Cette option convient à un environnement privé de test. Créez un fichier temporaire
hors du dépôt, protégez-le, puis chargez-le dans Kubernetes :

```bash
umask 077
vi /tmp/openmaster-secrets.env
kubectl create secret generic openmaster-secrets \
  --namespace openmaster \
  --from-env-file=/tmp/openmaster-secrets.env
rm /tmp/openmaster-secrets.env
```

Le fichier doit contenir exactement les huit clés listées précédemment. Utilisez des
mots de passe aléatoires forts et le même utilisateur, mot de passe et nom de base dans
`DATABASE_URL` et dans les variables `POSTGRES_*`. Cette méthode évite d'inscrire les
secrets dans l'historique du shell.

Vérifiez uniquement les noms de clés, sans afficher leurs valeurs :

```bash
kubectl describe secret openmaster-secrets -n openmaster
```

## 5. Créer les valeurs du cluster

Créez un fichier local non versionné :

```bash
cp helm/openmaster/values-production.yaml /tmp/openmaster-k3s.yaml
vi /tmp/openmaster-k3s.yaml
```

Configuration minimale :

```yaml
externalSecrets:
  enabled: true
  existingSecretName: openmaster-secrets

api:
  image: harbor.lucaslamy.fr/private/openmaster/api:2.1.0

web:
  image: harbor.lucaslamy.fr/private/openmaster/web:2.1.0

workers:
  image: harbor.lucaslamy.fr/private/openmaster/api:2.1.0

postgresql:
  persistence:
    storageClassName: local-path
    size: 20Gi

minio:
  persistence:
    storageClassName: local-path
    size: 50Gi

ingress:
  enabled: true
  className: nginx
  controllerNamespace: kube-system
  controllerPodLabels:
    app.kubernetes.io/name: nginx
  host: openmaster.lucaslamy.fr
  tls:
    enabled: true
    secretName: openmaster-tls
```

Remplacez les images et le domaine. Créez le Secret TLS avant le déploiement, par
exemple à partir d'un certificat existant :

```bash
kubectl create secret tls openmaster-tls \
  --namespace openmaster \
  --cert=/chemin/fullchain.pem \
  --key=/chemin/privkey.pem
```

En environnement de test uniquement, vous pouvez désactiver TLS dans le fichier :

```yaml
ingress:
  tls:
    enabled: false
    secretName: ""
```

Ajoutez un enregistrement DNS pointant `openmaster.example.com` vers l'adresse IP du
load balancer ou d'un nœud exposant Traefik.

## 6. Valider puis déployer

Le préflight vérifie le chart, le rendu Helm, l'accès au cluster, le Secret et toutes
les clés attendues sans afficher leur contenu :

```bash
export NAMESPACE=openmaster
export RELEASE=openmaster
export VALUES=/tmp/openmaster-k3s.yaml
export SECRET_NAME=openmaster-secrets

deployment/scripts/preflight-check.sh
deployment/scripts/deploy.sh
```

Le déploiement est atomique. Lors d'une première installation, Helm attend que les
services — notamment PostgreSQL interne — soient disponibles, puis exécute la migration
Alembic comme hook `post-install`. Lors d'une mise à niveau, la base existe déjà et la
migration s'exécute en `pre-upgrade`. Helm restaure automatiquement la release
précédente en cas d'échec.

## 7. Vérifier l'installation

```bash
helm status openmaster -n openmaster
kubectl get pods,svc,ingress,hpa,pdb -n openmaster
kubectl get pvc -n openmaster
kubectl get networkpolicy -n openmaster
deployment/scripts/smoke-test.sh
```

Pour suivre les composants :

```bash
kubectl logs -n openmaster deployment/openmaster-openmaster-api --tail=100
kubectl logs -n openmaster deployment/openmaster-openmaster-analysis-worker --tail=100
kubectl get events -n openmaster --sort-by=.lastTimestamp
```

Testez enfin l'accès public :

```bash
curl -fsS https://openmaster.example.com/
```

## 8. Mettre à jour ou revenir en arrière

Publiez les nouvelles images, modifiez leurs tags dans `/tmp/openmaster-k3s.yaml`, puis
relancez :

```bash
VALUES=/tmp/openmaster-k3s.yaml deployment/scripts/deploy.sh
helm history openmaster -n openmaster
deployment/scripts/rollback.sh REVISION
```

Le rollback Helm ne restaure pas automatiquement une migration de base de données.
Avant une mise à jour importante, vérifiez la compatibilité descendante de la migration
et testez la restauration d'une sauvegarde PostgreSQL.

## Services de données externes

Pour désactiver un service interne, fournissez son nom DNS et son port :

```yaml
postgresql:
  enabled: false
  externalHost: postgres.internal.example
  externalPort: 5432

redis:
  enabled: false
  externalHost: redis.internal.example
  externalPort: 6379

minio:
  enabled: false
  externalHost: minio.internal.example
  externalPort: 9000
```

Les NetworkPolicies ne savent pas autoriser un FQDN. Ajoutez donc les CIDR exacts des
destinations :

```yaml
networkPolicy:
  externalEgress:
    postgresql:
      - cidr: 10.20.30.40/32
    redis:
      - cidr: 10.20.30.41/32
    minio:
      - cidr: 10.20.30.42/32
```

N'utilisez pas `0.0.0.0/0`. Mettez aussi à jour les URL stockées dans Vault avec les
hôtes externes.

## Diagnostic rapide

- `ImagePullBackOff` : vérifiez les tags, l'accès au registre et `imagePullSecrets`.
- PVC en `Pending` : vérifiez `storageClassName`, la capacité et `kubectl describe pvc`.
- migration en échec : consultez le Job `openmaster-openmaster-migrate` et vérifiez
  `DATABASE_URL`.
- HPA sans métriques : vérifiez `kubectl top pods -n openmaster` et metrics-server.
- timeout réseau : contrôlez les labels DNS/Traefik et les CIDR de NetworkPolicy.
- erreur TLS ou 404 : contrôlez le DNS, l'IngressClass, le Secret TLS et Traefik.

Consultez aussi [`troubleshooting.md`](troubleshooting.md) et
[`production-checklist.md`](production-checklist.md).
