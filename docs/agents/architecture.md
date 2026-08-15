# Architecture de référence pour les agents

## Flux runtime

```text
Navigateur
  -> Vue/Vite servi par Nginx
  -> FastAPI
       -> PostgreSQL : utilisateurs, sessions, jobs et état durable
       -> MinIO/S3 : sources, rendus et objets audio
       -> Redis/Celery : file et dispatch éphémères
            -> worker analysis
            -> worker mastering
            -> worker export
```

Les routes API restent une couche de validation/orchestration. Le métier audio et
les services persistants vivent dans `packages/`; aucune application ne doit importer
directement une autre application.

## Ownership technique

- Backend : API, auth, database, storage, job store et services de jobs.
- Audio/DSP : audio core, analysis engine, DSP engine, mastering assistant, IA et
  compute backends.
- Workers : runtime Celery, entrées `openmaster-worker` et `runpod_worker`.
- Frontend : `apps/web/`, contrats HTTP et expérience utilisateur.
- Platform : Dockerfiles, `.dockerignore`, Helm, scripts et documentation deployment.

## Topologie k3s actuelle

Le chart déploie l’API, le web, trois workers, PostgreSQL et Redis dans
`openmaster`. L’Ingress Traefik route `/api` vers l’API et `/` vers le web.
PostgreSQL utilise un volume Longhorn et un sous-répertoire `PGDATA`; Redis n’est
pas migré comme donnée durable. MinIO reste partagé depuis `clipforge` via un
`ExternalName`, avec les secrets fournis par le SecretStore global.

Les images sont tirées depuis Harbor. Les certificats et le tunnel Cloudflare sont
des dépendances d’infrastructure : ils doivent être vérifiés dans le cluster, sans
mettre de valeurs secrètes dans Git.

## Livraison

Le chemin opératoire est : preflight -> Helm deploy -> vérification des rollouts ->
smoke test. Le rollback utilise le script dédié et une révision Helm connue. Les
tests via port-forward sont préférés au proxy d’API Kubernetes lorsque les
NetworkPolicies de production bloquent ce dernier.
