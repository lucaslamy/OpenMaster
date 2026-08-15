# Tests, contexte et garde-fous

## Validation proportionnelle

| Changement | Minimum attendu |
| --- | --- |
| Documentation/configuration sans runtime | `git diff --check`, liens/fichiers vérifiés |
| Python backend/package | tests ciblés puis `pytest -q` si le contrat commun est touché |
| Frontend | tests ciblés puis `npm test -- --run` si le build/UI est touché |
| Helm/deployment | `helm lint`, `validate-chart.sh`, rendu ciblé et rollback relu |
| Auth, secret, image ou exposition réseau | tests concernés + revue SECURITY |
| Release ou migration | validation complète + plan de rollback + revue RELEASE |

Un test non exécuté doit être explicitement signalé avec sa raison.

## Économie de contexte

- Charger d’abord `AGENTS.md`, puis uniquement les documents du domaine concerné.
- Rechercher les symboles et fichiers ciblés avant de lire des arbres complets.
- Passer aux spécialistes seulement les contrats, chemins et tests nécessaires.
- Éviter de répéter une baseline déjà validée ; chaque handoff ne contient que les
  changements, résultats et risques.

## Bloc d’impact production

Toute proposition de mutation de cluster doit inclure :

```text
DEPLOYMENT IMPACT
Namespace:
Release:
Images:
Migrations:
Stateful workloads affected:
Expected downtime:
Rollback:
```

Sans ce bloc, l’agent s’arrête à l’inspection et ne lance pas la mutation.

## Règles de sécurité

- Aucun secret en clair dans les logs, sorties, commits, manifests ou handoffs.
- Aucun `delete`, suppression de PVC/volume, purge de bucket, rollback destructif ou
  action équivalente sans confirmation explicite et cible vérifiée.
- Ne pas modifier manuellement le schéma PostgreSQL en production : utiliser
  Alembic et vérifier le backup/restauration.
- Évaluer Redis comme état éphémère avant toute tentative de migration ; ne pas
  fabriquer un backup qui n’est pas requis par l’application.
- Pour une bascule, garder l’ancien cluster disponible 24–48 h minimum et documenter
  le retour du trafic, des images, de la base et du stockage.
