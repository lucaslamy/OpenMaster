# Conseil de mastering avec LamAI

OpenMaster peut demander à la passerelle privée LamAI de proposer les réglages du
mastering. LamAI ne traite pas le son : le rendu reste assuré par la chaîne DSP
déterministe et reproductible d’OpenMaster.

## Données transmises

Lorsque l’utilisateur active l’option, le worker de mastering envoie à
`POST /v1/chat` :

- les mesures structurées de l’analyse ;
- les réglages initialement sélectionnés ;
- les limites autorisées pour chaque réglage.

Le fichier audio, les URL MinIO, les identifiants d’objet et les secrets ne sont
jamais inclus. La réponse du modèle doit contenir exactement tous les champs de
`MasteringPolicy`. OpenMaster refuse les champs manquants, inconnus, mal typés ou
hors limites.

Le preset sélectionné est transmis uniquement comme état « avant » pour l’audit.
LamAI reçoit explicitement la mission de reconstruire indépendamment tous les
contrôles ajustables à partir des mesures, sans considérer la cible LUFS ou les autres
valeurs demandées comme des préférences. Les fréquences et seuils internes non exposés
restent verrouillés : l’IA ne peut pas modifier la topologie DSP ni forcer un réglage
qui divergerait entre le worker local et RunPod. Lorsque les mesures ne suffisent pas
à justifier une correction spectrale, le prompt exige une intervention subtile plutôt
qu’une invention.

En cas de timeout, erreur HTTP ou réponse invalide, le job continue avec la politique
déterministe demandée. Le résultat `ai_assistance` indique `applied: false` et une
raison de repli non sensible.

## Configuration Vault

Copier la valeur de `LAMAI_CLIENT_API_KEY` dans le secret Vault d’OpenMaster sous la
clé `LAMAI_API_KEY`. Il s’agit de la clé cliente LamAI, pas de la clé RunPod détenue
par LamAI.

Le Secret Kubernetes `openmaster-secrets` doit ensuite contenir `LAMAI_API_KEY`.

## Valeurs Helm k3s

```yaml
lamai:
  enabled: true
  baseUrl: http://lamai-api.lamai.svc.cluster.local:8080
  timeoutSeconds: 120
  servicePort: 8080
  networkPolicy:
    namespaceSelector:
      kubernetes.io/metadata.name: lamai
    podSelector:
      app.kubernetes.io/name: lamai-api
```

Si la NetworkPolicy LamAI est activée, son entrée doit également autoriser les pods
`mastering-worker` du namespace `openmaster` sur le port 8080. Une politique réseau
est appliquée dans les deux directions : autoriser seulement la sortie OpenMaster ne
suffit pas.

Vérifier depuis le worker sans afficher la clé :

```bash
kubectl exec -n openmaster \
  deployment/openmaster-openmaster-mastering-worker \
  -- python -c \
  'import urllib.request; print(urllib.request.urlopen("http://lamai-api.lamai.svc.cluster.local:8080/health/live", timeout=5).status)'
```

## Résultat auditable

`recommendation.ai_assistance` et `mastering_result.ai_assistance` exposent :

- `requested` : option demandée par l’utilisateur ;
- `applied` : politique LamAI validée et utilisée ;
- `model` et `rationale` uniquement si le conseil a été appliqué ;
- `fallback_reason` lorsque la politique initiale a été conservée.

Le secret LamAI et le prompt complet ne sont jamais persistés.
L’interface affiche également un audit visuel de la recommandation :

- modèle LamAI ayant produit la proposition ;
- justification textuelle ;
- valeur demandée et valeur IA pour chaque réglage modifié ;
- position avant/après sur l’étendue autorisée du contrôle ;
- indication explicite du repli déterministe lorsque LamAI est indisponible.

Les données persistées dans `mastering_result.ai_assistance` incluent
`settings_before`, `settings_after` et `changes`. Elles correspondent aux réglages
exacts transmis au moteur DSP déterministe. Les anciens jobs créés avant cette
évolution ne disposent pas de cette comparaison et doivent être relancés.
