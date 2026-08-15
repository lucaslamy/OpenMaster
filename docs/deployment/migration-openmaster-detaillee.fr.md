# Migration détaillée des données OpenMaster

Cette procédure est spécifique au chart `helm/openmaster` et au code de ce dépôt.
Elle suppose que les objets MinIO ont déjà été copiés vers la cible.

## Données à migrer

OpenMaster utilise exactement ces services de données :

| Service | Contenu | Traitement |
| --- | --- | --- |
| PostgreSQL | comptes, sessions, projets, analyses, états de jobs et réglages | sauvegarder puis restaurer |
| MinIO partagé `clipforge/minio` | sources audio, prévisualisations et masters | déjà migré, contrôler les références |
| Redis | files Celery et résultats temporaires | ne pas sauvegarder/restaurer |

Le Redis du chart est explicitement configuré avec `persistence.enabled: false` : il n’y
a donc pas de PVC, de RDB ou d’AOF Redis à copier. Il n’y a pas besoin de migration Redis.
Les files Celery, verrous, résultats temporaires et messages en attente sont volatils ;
la cible démarre avec un Redis neuf. Ne copiez pas un dump Redis et ne réutilisez pas le
PVC d’un autre service.

Les jobs `queued`, `running`, `mastering` et `retry_wait` de l’ancien environnement ne
seront pas rejoués automatiquement, puisque leurs messages Celery ne sont pas migrés.
Après l’arrêt des workers, un état `running` ancien peut donc rester dans PostgreSQL :
c’est un historique à ignorer, pas une donnée Redis à restaurer. Les états
`analyzed`, `succeeded` et `failed` restent conservés dans PostgreSQL.

La source OpenMaster utilise le MinIO partagé de `clipforge` via un Service
`ExternalName`, et non un StatefulSet MinIO OpenMaster :

```text
MinIO interne : minio.clipforge.svc.cluster.local:9000
Endpoint public : https://s3.lucaslamy.fr
Bucket : openmaster
```

Les migrations Alembic du projet vont de `0001` à `0012`. La cible doit finir sur
`alembic_version = 0012`.

## 0. Construire les trois images avant la migration

Les Dockerfiles ont été durcis pour maintenir chaque couche sous 100 Mo : le wheelhouse
est monté temporairement pendant l’installation, NumPy et SciPy sont séparés, FFmpeg et
FFprobe sont copiés comme binaires statiques dans deux couches distinctes, et le contexte
exclut les caches, `node_modules` et les artefacts de build. L’image Web est multi-stage
et ne contient que le résultat Vite dans l’image Nginx.

Depuis le serveur qui possède le dépôt et le droit de pousser vers Harbor :

```bash
export VERSION="3.6.1-layered"
export REGISTRY="harbor.lucaslamy.fr/private/openmaster"
export RUNPOD_REGISTRY="harbor.lucaslamy.fr/library/openmaster-runpod"
docker login harbor.lucaslamy.fr

docker buildx build --platform linux/amd64 --load \
  -f Dockerfile.api -t "${REGISTRY}/api:${VERSION}" .
docker buildx build --platform linux/amd64 --load \
  -f Dockerfile.web -t "${REGISTRY}/web:${VERSION}" .
docker buildx build --platform linux/amd64 --load \
  -f Dockerfile.runpod -t "${RUNPOD_REGISTRY}:${VERSION}" .
```

Contrôlez chaque image avant de la publier. La colonne `SIZE` de `docker history` est
volontairement contrôlée en octets non compressés, donc plus stricte que la taille des
couches stockées dans Harbor : aucune ligne ne doit dépasser `100MB`.

```bash
for image in \
  "${REGISTRY}/api:${VERSION}" \
  "${REGISTRY}/web:${VERSION}" \
  "${RUNPOD_REGISTRY}:${VERSION}"; do
  echo "=== ${image} ==="
  docker history --no-trunc --format '{{.Size}}\t{{.CreatedBy}}' "${image}"
done
```

Si une ligne dépasse 100 Mo, ne poussez pas l’image et corrigez le Dockerfile avant de
continuer. Une fois les trois contrôles passés :

```bash
docker push "${REGISTRY}/api:${VERSION}"
docker push "${REGISTRY}/web:${VERSION}"
docker push "${RUNPOD_REGISTRY}:${VERSION}"
```

Le nœud k3s doit ensuite pouvoir résoudre `harbor.lucaslamy.fr`, faire confiance à son
certificat TLS et tirer ces trois références. N’imprimez jamais la configuration de
connexion au registry ni un secret Kubernetes.

Le registry Harbor ne doit pas être publié derrière le proxy Cloudflare pour les pushes
Docker volumineux. Utilisez pour `harbor.lucaslamy.fr` un enregistrement DNS-only vers
l’origine Harbor, ou un endpoint privé accessible depuis le serveur de build et les nœuds
k3s. Le proxy Cloudflare peut répondre `413 Payload Too Large` avant même que Harbor ne
reçoive le blob. Le hostname applicatif `openmaster.lucaslamy.fr` peut rester derrière
Cloudflare Tunnel ; cette contrainte concerne le hostname du registry.

## 1. Variables

Sur l’ancien serveur :

```bash
export KUBE_CONTEXT="default"
export NAMESPACE="openmaster"
export RELEASE="openmaster"
export BACKUP_DIR="/var/backups/openmaster-migration-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p -- "${BACKUP_DIR}"
chmod 700 -- "${BACKUP_DIR}"
```

Sur le nouveau serveur :

```bash
export KUBE_CONTEXT="default"
export NAMESPACE="openmaster"
export RELEASE="openmaster"
export DUMP_FILE="/var/backups/openmaster-postgres.dump"
export SOURCE_COUNTS_FILE="/var/backups/postgres-counts.txt"
export TARGET_COUNTS_FILE="/var/backups/postgres-counts-target.txt"
```

Les commandes de l’ancien serveur et celles du nouveau serveur ne doivent pas être
exécutées sur la même machine par erreur.

Ne faites jamais `kubectl get secret -o yaml` et n’affichez jamais une valeur de secret.
Les commandes ci-dessous utilisent les variables déjà injectées dans les conteneurs
PostgreSQL sans les imprimer.

## 2. Inventaire read-only de l’ancien serveur

```bash
kubectl --context "${KUBE_CONTEXT}" get nodes
kubectl --context "${KUBE_CONTEXT}" get statefulset,deploy,pod,svc,pvc -n "${NAMESPACE}"
helm --kube-context "${KUBE_CONTEXT}" status "${RELEASE}" -n "${NAMESPACE}"
helm --kube-context "${KUBE_CONTEXT}" history "${RELEASE}" -n "${NAMESPACE}"
```

Vérifiez que PostgreSQL est bien celui du chart, et non une base externe :

```bash
kubectl --context "${KUBE_CONTEXT}" get service \
  "${RELEASE}-openmaster-postgres" -n "${NAMESPACE}" \
  -o custom-columns=TYPE:.spec.type,EXTERNAL_NAME:.spec.externalName,CLUSTER_IP:.spec.clusterIP
```

La sortie attendue est `ClusterIP` avec `EXTERNAL_NAME` vide. Si le service est
`ExternalName`, arrêtez-vous et sauvegardez la base externe avec sa procédure dédiée.

Identifiez le pod PostgreSQL :

```bash
export PG_POD="$(kubectl --context "${KUBE_CONTEXT}" get pod -n "${NAMESPACE}" \
  -l app.kubernetes.io/component=postgresql \
  -o jsonpath='{.items[0].metadata.name}')"
test -n "${PG_POD}"
kubectl --context "${KUBE_CONTEXT}" get pod "${PG_POD}" -n "${NAMESPACE}"
```

Contrôlez les jobs en cours :

```bash
kubectl --context "${KUBE_CONTEXT}" exec -n "${NAMESPACE}" "${PG_POD}" \
  -c postgres -- \
  sh -ceu '
    export PGPASSWORD="$POSTGRES_PASSWORD"
    psql --host=127.0.0.1 --port=5432 \
      --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" \
      --tuples-only --no-align \
      --command="select status, count(*) from analysis_jobs group by status order by status;"
  '
```

Les états `queued`, `running`, `mastering` et `retry_wait` sont normalement des
traitements non terminés. Identifiez toutefois leur ancienneté avec `updated_at` : un
job `running` depuis plusieurs semaines peut être considéré comme obsolète si aucun
worker ne le traite encore.

Les jobs obsolètes peuvent être conservés tels quels dans PostgreSQL pour préserver leur
historique. Ne tentez pas de les relancer via Redis. Les états `analyzed`, `succeeded` et
`failed` sont durables et doivent être conservés.

## 3. Geler l’ancien OpenMaster

Enregistrez les réplicas actuels afin de pouvoir les rétablir :

```bash
kubectl --context "${KUBE_CONTEXT}" get deploy -n "${NAMESPACE}" \
  -o custom-columns=NAME:.metadata.name,REPLICAS:.spec.replicas,READY:.status.readyReplicas \
  | tee "${BACKUP_DIR}/old-deployments.txt"
```

Après validation de la fenêtre de maintenance, arrêtez l’API, le Web et les workers.
Cette action ne supprime ni release, ni PVC, ni données :

```bash
for deployment in \
  "${RELEASE}-openmaster-api" \
  "${RELEASE}-openmaster-web" \
  "${RELEASE}-openmaster-analysis-worker" \
  "${RELEASE}-openmaster-mastering-worker" \
  "${RELEASE}-openmaster-export-worker"; do
  kubectl --context "${KUBE_CONTEXT}" scale "deployment/${deployment}" \
    --replicas=0 -n "${NAMESPACE}"
done
kubectl --context "${KUBE_CONTEXT}" get pod -n "${NAMESPACE}"
```

Laissez les StatefulSets PostgreSQL et MinIO en fonctionnement. Redis n’a pas besoin
d’être exporté. Après l’arrêt des API/workers, les jobs `running` obsolètes resteront
visibles mais ne progresseront plus ; c’est attendu dans cette migration. Les éventuels
messages restés dans le Redis source ne seront pas consommés par la cible.

## 4. Dump PostgreSQL sur l’ancien serveur

Créez un dump custom directement depuis le conteneur PostgreSQL :

```bash
kubectl --context "${KUBE_CONTEXT}" exec -n "${NAMESPACE}" "${PG_POD}" \
  -c postgres -- \
  sh -ceu '
    export PGPASSWORD="$POSTGRES_PASSWORD"
    pg_dump \
      --host=127.0.0.1 \
      --port=5432 \
      --username="$POSTGRES_USER" \
      --dbname="$POSTGRES_DB" \
      --format=custom \
      --no-owner \
      --no-privileges
  ' > "${BACKUP_DIR}/openmaster-postgres.dump"
chmod 600 -- "${BACKUP_DIR}/openmaster-postgres.dump"
test -s "${BACKUP_DIR}/openmaster-postgres.dump"
```

Contrôlez l’archive et son empreinte sans afficher les données :

```bash
cat "${BACKUP_DIR}/openmaster-postgres.dump" \
  | kubectl --context "${KUBE_CONTEXT}" exec -i \
      -n "${NAMESPACE}" "${PG_POD}" -c postgres -- \
      pg_restore --list \
  | grep -E 'TABLE|TABLE DATA|SEQUENCE' | sed -n '1,100p'
sha256sum "${BACKUP_DIR}/openmaster-postgres.dump" \
  | tee "${BACKUP_DIR}/openmaster-postgres.dump.sha256"
```

Enregistrez les compteurs de référence :

```bash
kubectl --context "${KUBE_CONTEXT}" exec -n "${NAMESPACE}" "${PG_POD}" -- \
  sh -ceu '
    export PGPASSWORD="$POSTGRES_PASSWORD"
    psql --host=127.0.0.1 --port=5432 \
      --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" \
      --tuples-only --no-align --command="
        select count(*) from users;
        select count(*) from user_sessions;
        select count(*) from analysis_jobs;
        select status, count(*) from analysis_jobs group by status order by status;
      "
  ' | tee "${BACKUP_DIR}/postgres-counts.txt"
```

## 5. Transfert sécurisé du dump

Depuis l’ancien serveur, utilisez votre hôte SSH réel :

```bash
scp -p "${BACKUP_DIR}/openmaster-postgres.dump" \
  debian@51.36.226.100:/var/backups/openmaster-postgres.dump
scp -p "${BACKUP_DIR}/openmaster-postgres.dump.sha256" \
  debian@51.36.226.100:/var/backups/openmaster-postgres.dump.sha256
scp -p "${BACKUP_DIR}/postgres-counts.txt" \
  debian@51.36.226.100:/var/backups/postgres-counts.txt
```

Sur le nouveau serveur :

```bash
chmod 600 -- "${DUMP_FILE}" "${DUMP_FILE}.sha256"
sha256sum --check "${DUMP_FILE}.sha256"
chmod 600 -- /var/backups/postgres-counts.txt
```

## 6. Préparer le nouveau cluster et les secrets

Sur le nouveau serveur :

```bash
kubectl --context "${KUBE_CONTEXT}" get nodes -o wide
kubectl --context "${KUBE_CONTEXT}" top nodes
kubectl --context "${KUBE_CONTEXT}" get storageclass longhorn
kubectl --context "${KUBE_CONTEXT}" get ingressclass traefik
kubectl --context "${KUBE_CONTEXT}" get clustersecretstore vault-global
kubectl --context "${KUBE_CONTEXT}" get secret openmaster-tls -n "${NAMESPACE}"
getent hosts harbor.lucaslamy.fr
```

Créez et étiquetez le namespace :

```bash
kubectl --context "${KUBE_CONTEXT}" create namespace "${NAMESPACE}" \
  --dry-run=client -o yaml | kubectl --context "${KUBE_CONTEXT}" apply -f -
kubectl --context "${KUBE_CONTEXT}" label namespace "${NAMESPACE}" \
  openmaster.io/secrets=enabled --overwrite
```

Dans `deployment/examples/cluster-external-secret.example.yaml`, remplacez
`REPLACE_WITH_VAULT_PATH` par le chemin Vault réel. Ne remplacez pas `vault-global` et
n’ajoutez aucune valeur secrète au dépôt. L’exemple est un `ClusterExternalSecret` qui
sélectionne le namespace étiqueté `openmaster.io/secrets=enabled`. Appliquez ensuite :

```bash
kubectl --context "${KUBE_CONTEXT}" apply \
  -f deployment/examples/cluster-external-secret.example.yaml
kubectl --context "${KUBE_CONTEXT}" get externalsecret -n "${NAMESPACE}"
kubectl --context "${KUBE_CONTEXT}" describe secret openmaster-secrets -n "${NAMESPACE}"
```

Attendez un ExternalSecret `Ready` et la présence de `openmaster-secrets`. Ne poursuivez
pas si une clé est absente.

## 7. Déployer uniquement les services de données

Ne lancez pas encore le déploiement production complet. Depuis la racine du dépôt sur
le nouveau serveur :

```bash
export CHART="helm/openmaster"
export VALUES="${CHART}/values-production.yaml"

helm upgrade --install "${RELEASE}" "${CHART}" \
  --kube-context "${KUBE_CONTEXT}" \
  --namespace "${NAMESPACE}" --create-namespace \
  -f "${CHART}/values.yaml" -f "${VALUES}" \
  --set migration.enabled=false \
  --set autoscaling.enabled=false \
  --set api.replicaCount=0 \
  --set web.replicaCount=0 \
  --set workers.analysis.replicaCount=0 \
  --set workers.mastering.replicaCount=0 \
  --set workers.export.replicaCount=0 \
  --atomic --wait --timeout 20m
```

Vérifiez d’abord le raccordement MinIO externe :

```bash
kubectl --context "${KUBE_CONTEXT}" get service \
  "${RELEASE}-openmaster-minio" -n "${NAMESPACE}" \
  -o custom-columns=TYPE:.spec.type,EXTERNAL_NAME:.spec.externalName,PORT:.spec.ports[*].port
```

La sortie attendue est `ExternalName`, `minio.clipforge.svc.cluster.local` et `9000`.
Il ne doit pas y avoir de pod ni de PVC MinIO OpenMaster.

Vérifiez ensuite PostgreSQL :

```bash
kubectl --context "${KUBE_CONTEXT}" rollout status \
  statefulset/${RELEASE}-openmaster-postgres -n "${NAMESPACE}" --timeout=10m
export PG_POD="$(kubectl --context "${KUBE_CONTEXT}" get pod -n "${NAMESPACE}" \
  -l app.kubernetes.io/component=postgresql \
  -o jsonpath='{.items[0].metadata.name}')"
test -n "${PG_POD}"
kubectl --context "${KUBE_CONTEXT}" exec -n "${NAMESPACE}" "${PG_POD}" -- \
  sh -ceu '
    export PGPASSWORD="$POSTGRES_PASSWORD"
    psql --host=127.0.0.1 --port=5432 \
      --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" \
      --tuples-only --no-align \
      --command="\\dt"
  '
```

La base doit être vide : `psql` doit indiquer qu’aucune relation n’existe. Si des tables existent,
arrêtez-vous. N’utilisez pas `pg_restore --clean` sans une confirmation explicite et une
sauvegarde de la base cible.

Le chart configure PostgreSQL avec `PGDATA=/var/lib/postgresql/data/pgdata`. Ce sous-
répertoire est nécessaire avec Longhorn, car la racine d’un volume ext4 contient souvent
`lost+found`. Ne nettoyez pas et ne reformatez pas le PVC pour contourner cette erreur.

Vérifiez également que Redis est bien une instance neuve et éphémère :

```bash
kubectl --context "${KUBE_CONTEXT}" get statefulset,pod,pvc -n "${NAMESPACE}" \
  -l app.kubernetes.io/component=redis
```

La commande doit montrer le StatefulSet Redis du chart sans PVC Redis. Ne restaurez rien
dans ce Redis ; sa seule validation à ce stade est son état `Ready`.

## 8. Restaurer PostgreSQL sur la cible

La commande suivante écrit seulement dans la base cible vide :

```bash
cat "${DUMP_FILE}" | kubectl --context "${KUBE_CONTEXT}" exec -i \
  -n "${NAMESPACE}" "${PG_POD}" -- \
  sh -ceu '
    export PGPASSWORD="$POSTGRES_PASSWORD"
    pg_restore \
      --host=127.0.0.1 \
      --port=5432 \
      --username="$POSTGRES_USER" \
      --dbname="$POSTGRES_DB" \
      --no-owner \
      --no-privileges \
      --exit-on-error \
      --format=custom
  '
```

Comparez immédiatement les compteurs avec le fichier de référence :

```bash
kubectl --context "${KUBE_CONTEXT}" exec -n "${NAMESPACE}" "${PG_POD}" -- \
  sh -ceu '
    export PGPASSWORD="$POSTGRES_PASSWORD"
    psql --host=127.0.0.1 --port=5432 \
      --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" \
      --tuples-only --no-align --command="
        select count(*) from users;
        select count(*) from user_sessions;
        select count(*) from analysis_jobs;
        select status, count(*) from analysis_jobs group by status order by status;
      "
  ' > "${TARGET_COUNTS_FILE}"
diff -u "${SOURCE_COUNTS_FILE}" "${TARGET_COUNTS_FILE}"
```

Toute différence doit être expliquée avant de démarrer l’application.

## 9. Vérifier les références MinIO déjà migrées

Les références PostgreSQL doivent pointer vers des objets présents dans le bucket cible :

```bash
kubectl --context "${KUBE_CONTEXT}" exec -n "${NAMESPACE}" "${PG_POD}" -- \
  sh -ceu '
    export PGPASSWORD="$POSTGRES_PASSWORD"
    psql --host=127.0.0.1 --port=5432 \
      --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" \
      --tuples-only --no-align --command="
        select object_name from analysis_jobs where object_name is not null
        union select output_object_name from analysis_jobs where output_object_name is not null
        union select initial_output_object_name from analysis_jobs where initial_output_object_name is not null
        order by 1;
      "
  ' > "${DUMP_FILE}.object-references.txt"
```

Avec votre alias `mc` déjà configuré vers MinIO cible :

```bash
mc stat "<alias-minio>/openmaster"
while IFS= read -r object_name; do
  test -z "${object_name}" || \
    mc stat "<alias-minio>/openmaster/${object_name}" >/dev/null
done < "${DUMP_FILE}.object-references.txt"
```

Un message `Insufficient permissions` ou HTTP 403 ne signifie pas que l’objet est
absent : l’alias `mc` n’a probablement pas `s3:GetObject` sur le bucket `openmaster`.
Refaites le test avec un alias d’administration déjà configuré, sans afficher ses
identifiants. Si l’alias administrateur voit l’objet mais pas l’alias applicatif, faites
ajuster la policy MinIO de l’utilisateur applicatif pour autoriser au minimum
`s3:GetBucketLocation`, `s3:ListBucket` et `s3:GetObject` sur `openmaster` et les
préfixes utilisés par OpenMaster. Ne rendez pas le bucket public.

Tout objet réellement absent bloque la bascule DNS.

## 10. Activer Alembic et l’application

Quand PostgreSQL et MinIO sont cohérents :

```bash
export VALUES="helm/openmaster/values-production.yaml"
KUBE_CONTEXT="${KUBE_CONTEXT}" deployment/scripts/preflight-check.sh
KUBE_CONTEXT="${KUBE_CONTEXT}" deployment/scripts/deploy.sh
```

Le hook de migration exécute `alembic upgrade head`. Vérifiez la révision :

```bash
kubectl --context "${KUBE_CONTEXT}" exec -n "${NAMESPACE}" "${PG_POD}" -- \
  sh -ceu '
    export PGPASSWORD="$POSTGRES_PASSWORD"
    psql --host=127.0.0.1 --port=5432 \
      --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" \
      --tuples-only --no-align --command="select version_num from alembic_version;"
  '
```

La valeur attendue est `0012`. Contrôlez ensuite :

```bash
kubectl --context "${KUBE_CONTEXT}" get job,pod,svc,ingress,pvc -n "${NAMESPACE}"
KUBE_CONTEXT="${KUBE_CONTEXT}" deployment/scripts/smoke-test.sh
```

## 11. Tests fonctionnels avant bascule DNS

Testez sur `https://openmaster.lucaslamy.fr` :

1. connexion avec un compte PostgreSQL restauré ;
2. affichage de l’historique des projets ;
3. ouverture et lecture d’une source MinIO existante ;
4. téléchargement d’un master existant ;
5. renommage d’un projet ;
6. création d’un petit job d’analyse ;
7. mastering de ce job ;
8. présence de son nouvel objet source/master dans MinIO ;
9. absence d’erreurs dans les logs API et workers.

Ne basculez pas le DNS si un compte, un projet ou un objet existant est inaccessible.

## 12. Bascule et conservation de l’ancien cluster

Après validation complète, faites pointer le DNS vers Traefik du nouveau cluster. Ne
supprimez rien sur l’ancien cluster. Laissez sa release, ses PVC PostgreSQL/MinIO et ses
sauvegardes disponibles pendant au moins 24 à 48 heures.

## 13. Rollback

### Avant toute nouvelle écriture sur la cible

Si la cible échoue avant la bascule ou avant toute nouvelle écriture :

```bash
KUBE_CONTEXT="${KUBE_CONTEXT}" deployment/scripts/rollback.sh REVISION
```

L’ancien cluster n’a pas été supprimé et peut rester la source de reprise.

### Après bascule, sans nouvelles écritures sur la cible

1. arrêtez l’API et les workers cibles ;
2. remettez le DNS vers l’ancien cluster ;
3. sur l’ancien serveur, remettez les réplicas enregistrés dans
   `${BACKUP_DIR}/old-deployments.txt` ;
4. vérifiez les données et les objets MinIO avant de rouvrir le trafic.

### Après de nouvelles écritures sur la cible

Ne faites pas un simple rollback DNS : il pourrait perdre des comptes, jobs ou réglages
créés depuis la bascule. Sauvegardez d’abord PostgreSQL et MinIO cible, puis décidez
explicitement d’une fusion ou d’un retour arrière. Le rollback Helm ne restaure ni les
données PostgreSQL, ni les migrations Alembic, ni les objets MinIO.
