# Routage et ownership

## Orchestrateur

L’orchestrateur est responsable de la reformulation du besoin, du découpage, des
interfaces, de la synthèse et de la validation finale. Il ne prend pas le ownership
du code d’un spécialiste par défaut.

## Domaines

| Domaine | Périmètre principal | Revue déclenchée |
| --- | --- | --- |
| BACKEND | `apps/api/`, auth, database, storage, jobs | migrations, contrats API |
| AUDIO-DSP | audio, analyse, DSP, IA, backends | exactitude audio, CPU, performance |
| WORKERS | runtime Celery, workers locaux et RunPod | idempotence, retry, queue |
| FRONTEND | `apps/web/` et contrats UI | accessibilité, régression UI |
| PLATFORM | Docker, Helm, deployment, opérations | sécurité, disponibilité, rollback |
| QA | stratégie et exécution des tests | toute modification à risque |
| SECURITY | secrets, auth, exposition et dépendances | auth, infra, images ou données |
| RELEASE | version, changelog, readiness | avant publication/bascule |

QA, SECURITY et RELEASE sont des rôles de revue : ils ne sont pas lancés comme
agents d’implémentation systématiques et n’ont pas d’ownership chevauchant.

## Modes de travail

- **SMALL / Fast Path** : un domaine propriétaire, changement local, tests ciblés,
  puis contrôle de l’orchestrateur.
- **MEDIUM** : orchestrateur + 2 ou 3 domaines, interfaces écrites avant les
  modifications parallèles, revue QA si le risque le justifie.
- **LARGE** : orchestrateur + spécialistes disjoints, baseline et plan de rollback,
  intégration séquentielle, revue QA/SECURITY/RELEASE obligatoire selon le périmètre.

## Handoff obligatoire

Chaque agent remet un rapport court :

```text
RESULT
Changed:
Tests:
Interfaces affected:
Risks:
Follow-up:
```

Un conflit de fichiers ou de contrat est remonté à l’orchestrateur ; un spécialiste
ne résout pas silencieusement le conflit en écrasant le travail d’un autre agent.
