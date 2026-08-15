# OpenMaster — contrat de travail multi-agent

Ce fichier décrit les règles d’intervention des agents et renvoie aux documents
détaillés sous [`docs/agents/`](docs/agents/README.md). Il ne change pas le runtime.

## Sources de vérité

- [`ARCHITECTURE.md`](ARCHITECTURE.md) : architecture logicielle actuelle.
- [`ROADMAP.md`](ROADMAP.md) : périmètre et séquencement produit.
- [`docs/agents/baseline.md`](docs/agents/baseline.md) : état mesuré du dépôt.
- [`docs/agents/routing.md`](docs/agents/routing.md) : routage, ownership et handoff.
- [`docs/agents/testing-and-safety.md`](docs/agents/testing-and-safety.md) : validation et sécurité.

En cas de divergence, le code et les manifests déployés priment sur une description
ancienne. Une modification d’architecture doit mettre à jour la documentation
correspondante.

## Architecture actuelle

Le navigateur utilise l’application Vue/Vite, servie par Nginx, puis l’API FastAPI.
L’API et les workers partagent les packages métier. PostgreSQL contient l’état
durable, MinIO/S3 les objets audio, et Redis/Celery le dispatch éphémère :

```text
Browser -> Web/Nginx -> FastAPI -> PostgreSQL
                              -> MinIO/S3
                              -> Redis/Celery -> analysis/mastering/export workers
```

Les frontières de packages et le déploiement Kubernetes sont détaillés dans
[`docs/agents/architecture.md`](docs/agents/architecture.md).

## Règles de code

- Garder les routes minces : validation et orchestration dans l’API, logique métier
  dans les services/packages.
- Préférer du Python typé, des modules explicites, des tâches Celery idempotentes et
  des migrations Alembic réversibles.
- Le traitement audio CPU doit rester fonctionnel et déterministe ; l’IA ne doit pas
  masquer le DSP déterministe.
- Ne jamais committer, afficher ou copier un secret en clair, ni journaliser des
  secrets ou du contenu audio.
- Ne pas ajouter de dépendance applicative directe entre deux applications ; partager
  le code dans `packages/`.

## Validation locale

```bash
pytest -q
cd apps/web && npm test -- --run
helm lint helm/openmaster -f helm/openmaster/values-production.yaml
deployment/scripts/validate-chart.sh
```

Adapter les tests aux fichiers touchés ; voir la matrice dans
[`docs/agents/testing-and-safety.md`](docs/agents/testing-and-safety.md).

## Routage et ownership

- Petite tâche : Fast Path, un agent propriétaire.
- Tâche moyenne : orchestrateur + deux ou trois spécialistes maximum.
- Grande tâche : orchestrateur, spécialistes disjoints, puis revue QA/sécurité selon
  le risque.

Le détail des domaines est dans [`docs/agents/routing.md`](docs/agents/routing.md).
Un agent ne modifie pas le domaine d’un autre sans handoff explicite et vérifiable.

## Production et Git

- Préserver les modifications préexistantes du worktree et les signaler ; ne pas les
  écraser pour simplifier une tâche.
- Toute mutation de cluster doit préciser namespace, release, images, migrations,
  workloads stateful, downtime attendu et rollback avant exécution.
- Ne jamais supprimer une ressource, un volume ou une donnée sans confirmation
  explicite. Conserver un ancien environnement disponible pendant une bascule.
- PostgreSQL se modifie via Alembic ; Redis est considéré comme état éphémère sauf
  décision documentée contraire. Les volumes persistants utilisent les conventions
  du cluster cible, notamment Longhorn si applicable.
- Utiliser SemVer et Conventional Commits. Mettre à jour `CHANGELOG.md` et la doc
  concernée pour tout changement significatif.

Les garde-fous complets et le format de rapport sont dans
[`docs/agents/testing-and-safety.md`](docs/agents/testing-and-safety.md).
