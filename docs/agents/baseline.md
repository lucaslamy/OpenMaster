# Baseline du dépôt

État relevé le 2026-08-15, sans secret ni contenu sensible.

## Version et Git

- Branche : `main`, suivie par `origin/main`.
- HEAD : `560bc62` (`move sourcecode`).
- Tag le plus proche : `v3.6.1`.
- Version applicative/chart : `3.6.1`.
- Le worktree contient déjà des changements de migration k3s, Docker, Helm et
  documentation ; ils sont préexistants à l’initialisation multi-agent et doivent
  être préservés.

## Validation de référence

- Python : `pytest -q` — 134 tests réussis.
- Web : `cd apps/web && npm test -- --run` — 6 fichiers, 28 tests réussis.
- Helm : `helm lint helm/openmaster -f helm/openmaster/values-production.yaml` — réussi.
- Chart : `deployment/scripts/validate-chart.sh` — 23 tests Helm réussis ;
  `kubeconform` absent, donc cette étape est ignorée par le script.

## Structure réelle

- `apps/api/` : frontière FastAPI.
- `apps/web/` : application Vue/Vite.
- `apps/openmaster-worker/` et `apps/runpod_worker/` : entrées workers.
- `packages/` : audio, analyse, DSP, IA, stockage, base, auth, jobs et runtime Celery.
- `tests/` : tests Python ; `apps/web/` contient les tests frontend.
- `helm/openmaster/` et `deployment/` : packaging et opérations Kubernetes.

## État de déploiement observé

Le cluster k3s cible utilise le contexte `default`, le namespace `openmaster`, Helm
release `openmaster`, Traefik et Longhorn. PostgreSQL est stateful, Redis est
éphémère, et MinIO est consommé via le Service `ExternalName` vers le namespace
`clipforge`. Les détails opérationnels de migration restent dans
[`docs/deployment/migration-openmaster-detaillee.fr.md`](../deployment/migration-openmaster-detaillee.fr.md).
