# Référence technique du mastering OpenMaster

> Référence du moteur v3.4, destinée à l’écoute critique et à l’audit par un
> ingénieur du son. Le code reste l’autorité en cas d’écart avec ce document.

Cette référence exhaustive est complétée dans l’interface par la page
**Technique**, accessible depuis la navigation principale. Elle présente la chaîne,
les détecteurs, le true peak, la frontière LamAI et l’export sous forme de schémas
animés et responsives. Les animations sont décoratives, respectent
`prefers-reduced-motion` et ne remplacent jamais les valeurs normatives de ce document.

## 1. Philosophie et périmètre

OpenMaster ne sélectionne pas une chaîne opaque à partir d’un genre musical. Un
master est le résultat reproductible de trois éléments :

1. le fichier source immuable ;
2. une analyse déterministe ;
3. une politique de mastering sérialisée contenant tous les réglages.

LamAI est un conseiller facultatif. Il peut proposer une autre politique, mais ne
traite jamais le son et ne peut ni ajouter un processeur caché, ni dépasser les
bornes du moteur. Le rendu final est toujours effectué par la même chaîne DSP
déterministe.

Le moteur travaille sur un tableau `float64` normalisé, de forme
`(nombre_d_images, nombre_de_canaux)`. Tous les processeurs conservent la fréquence
d’échantillonnage, le nombre d’images et le nombre de canaux. Ils retournent un
nouveau tampon et ne conservent pas d’état entre deux rendus.

OpenMaster n’effectue actuellement ni correction automatique de largeur stéréo, ni
compression multibande générale, ni matching spectral caché. Les traitements
fréquentiels réellement présents sont décrits ci-dessous.

## 2. Parcours exact d’un projet

Le parcours de production est :

1. **Choix du fichier** : aucune donnée audio n’est encore transférée.
2. **Compte** : l’API vérifie une session opaque `HttpOnly` avant l’upload. La source,
   les réglages, les aperçus et les masters sont ensuite rattachés au même utilisateur.
3. **Upload** : validation du format, stockage privé de la source dans MinIO et
   création du projet.
4. **Analyse** : décodage puis calcul des mesures décrites à la section 4.
5. **Pré-réglage live** : lecture de la source originale dans le navigateur et
   approximation locale des réglages compatibles avec Web Audio.
6. **Décision** : la politique courante est persistée. C’est seulement à ce moment
   qu’un rendu peut être demandé.
7. **Master** : le worker repart toujours de l’objet source immuable. Il ne remasterise
   jamais un ancien master.
8. **Contrôle et téléchargement** : le WAV, les mesures après traitement et la trace
   des processeurs sont conservés avec le projet.

Les vingt projets les plus récents sont exposés dans l’historique. La source, les
réglages, l’analyse et les informations de rendu sont conservés côté serveur ; les
liens de lecture et de téléchargement sont des URL signées temporaires.

## 3. Entrées, décodage et représentation

### WAV

Le décodeur natif accepte :

- PCM entier 8, 16, 24 et 32 bits ;
- IEEE float 32 et 64 bits.

Le PCM est converti en `float64` par division respectivement par `128`, `32768`,
`8388608` ou `2147483648`. Le WAV flottant doit contenir uniquement des valeurs
finies.

### Autres conteneurs

AIFF, FLAC, M4A, MP3, OGG et Opus sont sondés par FFprobe, puis décodés par FFmpeg en
PCM flottant 64 bits little-endian. OpenMaster sélectionne le premier flux audio. La
durée, la fréquence, le nombre de canaux, la taille décodée et les valeurs finies sont
contrôlés avant l’analyse.

Le moteur ne change pas volontairement la fréquence d’échantillonnage du programme.
Les suréchantillonnages ×4 des étages non linéaires sont internes et reviennent à la
fréquence source.

## 4. Analyse de la source

### Niveau

- **RMS global** :
  `20 log10(sqrt(moyenne(x²)))`, tous échantillons et canaux confondus.
- **Sample peak** :
  `20 log10(max(abs(x)))`.
- **True peak estimé** : maximum après suréchantillonnage polyphasé ×4.
- **Facteur de crête** : `sample_peak_dBFS - RMS_dBFS`.

Le plancher numérique utilisé par les conversions logarithmiques est `1e-12`.

### LUFS intégré

L’estimateur suit la structure de BS.1770 :

1. shelf K-weighting RBJ à `1681,974 Hz`, `+4 dB`, `Q = 0,707` ;
2. passe-haut Butterworth d’ordre 2 à `38,135 Hz` ;
3. blocs de `400 ms`, espacés de `100 ms` ;
4. niveau de bloc `-0,691 + 10 log10(énergie)` ;
5. gate absolue à `-70 LUFS` ;
6. gate relative à `10 LU` sous la moyenne des blocs ayant franchi la gate absolue.

Cette mesure est déterministe et adaptée au pilotage interne du moteur. Elle n’est
pas annoncée comme un appareil de conformité certifié EBU/ITU, notamment pour les
pondérations de dispositions multicanales particulières. Pour une livraison
réglementée, contrôler le WAV avec un mesureur certifié.

### Dynamique et contenu

- **Étendue dynamique** : différence entre les percentiles 95 et 10 des RMS calculés
  sur des fenêtres de 400 ms avec un recouvrement de 75 %.
- **Largeur stéréo** : `RMS(Side) / RMS(Mid)`, avec
  `Mid=(L+R)/2` et `Side=(L-R)/2`.
- **Corrélation de phase** : corrélation de Pearson entre gauche et droite.
- **Centroïde spectral** : moyenne fréquentielle pondérée par la magnitude d’une STFT
  de 2048 points au maximum, recouvrement 50 %.
- **BPM** : autocorrélation du flux spectral, recherche entre 60 et 200 BPM.
- **Tonalité** : chroma STFT comparé aux profils majeur/mineur de Krumhansl.

Le BPM et la tonalité sont des indications de contexte. Ils ne modifient pas la chaîne
de mastering actuelle.

## 5. Décision de gain automatique

La politique contient une cible `T`, le LUFS source mesuré `L` et une correction
maximale `M`.

```text
gain demandé = T - L
gain initial = limiter(gain demandé, -M, +M)
```

Une correction positive n’est pas bornée par le sample peak de la source. Ce choix est
intentionnel : une limitation par la crête brute empêchait les mixes denses
d’approcher la cible. Le clipper éventuel et le limiteur final sont responsables de la
sécurité des crêtes.

Si les LUFS ne sont pas disponibles, le gain d’entrée reste à `0 dB`. La décision
enregistre néanmoins la politique et sa justification.

### Calibration après limiteur

L’EQ, les étages non linéaires et le limiteur peuvent rendre la première estimation
imparfaite. OpenMaster mesure donc le LUFS de sortie et peut accepter au maximum deux
nouveaux rendus :

- tolérance d’arrêt : `±0,2 LU` ;
- correction d’une passe : au plus `±3 dB` ;
- déplacement cumulé autour du gain initial : au plus `±1 dB` ;
- respect permanent de la correction maximale `M` ;
- à partir d’une passe acceptée, utilisation possible de la réponse observée en
  `LU/dB`, seulement si elle vaut au moins `0,1 LU/dB` ;
- un candidat n’est conservé que si son erreur absolue à la cible diminue.

Le moteur préfère donc une erreur de cible documentée à une escalade indéfinie de la
réduction de gain. `loudness_correction_passes` et
`target_loudness_error_lu` figurent dans l’audit.

## 6. Ordre exact de la chaîne finale

L’ordre est fixe :

```text
Source
  → Passe-haut
  → EQ tonale trois bandes
  → EQ dynamique
  → Contrôle dynamique du grave
  → De-esser
  → Gain de niveau
  → Saturation
  → Clipper suréchantillonné
  → Limiteur lié suréchantillonné
  → Mesures de sortie
  → Quantification PCM et dither
```

### 6.1 Passe-haut

- Butterworth d’ordre 4 ;
- pente asymptotique : 24 dB/octave ;
- fréquence réglable : 15 à 80 Hz, 25 Hz par défaut ;
- application causale par sections de second ordre ;
- fréquence interne plafonnée à 45 % de la fréquence d’échantillonnage.

Le filtre peut être entièrement désactivé. Son rôle est de retirer l’infragrave, pas
d’amincir automatiquement la basse musicale.

### 6.2 EQ tonale

Trois filtres peaking RBJ causaux sont appliqués successivement :

| Bande | Fréquence | Q | Gain |
| --- | ---: | ---: | ---: |
| Grave | 100 Hz | 0,7 | −6 à +6 dB |
| Médium | 1 000 Hz | 1,0 | −6 à +6 dB |
| Aigu | 10 000 Hz | 0,7 | −6 à +6 dB |

Pour chaque bande, `A = 10^(gain/40)`, `ω = 2πf/Fs` et
`α = sin(ω)/(2Q)`. Les coefficients sont ceux du peaking EQ RBJ, normalisés par `a0`.
Une bande à `0 dB`, ou située au-dessus de 49 % de `Fs`, est contournée.

### 6.3 EQ dynamique

- centre par défaut : 2 500 Hz ;
- Q : 1,0 ;
- seuil : −18 dBFS ;
- ratio : 2:1 ;
- attaque : 12 ms ;
- release : 120 ms ;
- réduction maximale réglable : 0 à 12 dB.

Les bords de bande sont symétriques en octaves :
`largeur_octave = 1/Q`, puis
`f_basse = f_centre / 2^(largeur_octave/2)` et
`f_haute = f_centre × 2^(largeur_octave/2)`.

### 6.4 Contrôle du grave

- passe-bas Butterworth d’ordre 4 à 140 Hz ;
- seuil : −16 dBFS ;
- ratio : 3:1 ;
- attaque : 25 ms ;
- release : 180 ms ;
- réduction maximale réglable : 0 à 12 dB.

Seule la composante grave est atténuée. Le signal est reconstruit par
`sortie = source + grave × (gain - 1)`. Une réduction maximale à `0 dB` est un vrai
bypass.

### 6.5 De-esser

- bande centrée à 7 000 Hz ;
- Q de détection : 1,4 ;
- seuil : −22 dBFS ;
- ratio : 4:1 ;
- attaque : 2 ms ;
- release : 70 ms ;
- réduction maximale réglable : 0 à 12 dB.

L’EQ dynamique, le contrôle du grave et le de-esser utilisent un détecteur lié :
le maximum absolu de tous les canaux commande la même réduction pour préserver
l’image stéréo. Pour un niveau `D` au-dessus du seuil `S`, la réduction cible est :

```text
min(réduction_max, max(0, D-S) × (1 - 1/ratio))
```

L’enveloppe est lissée par
`état = coefficient × état + (1-coefficient) × cible`, avec
`coefficient = exp(-1/(Fs × temps))`.

Les bandes sélectives sont extraites par des Butterworth d’ordre 4, en aller-retour
zéro-phase pour les buffers de plus de 15 images. Cette extraction ne signifie pas que
toute la chaîne est linear-phase : le passe-haut et l’EQ tonale restent causaux.

### 6.6 Gain

Le gain décidé à la section 5 est un facteur fixe :

```text
sortie = entrée × 10^(gain_dB/20)
```

Il intervient après les correcteurs fréquentiels et avant les étages non linéaires.

### 6.7 Saturation

La saturation est réglée par `amount` entre 0 et 1 et fonctionne à `4 × Fs`.

```text
drive = 1 + 0,75 × amount
courbe = tanh(x × drive) / tanh(drive)
wet = 0,14 × amount
sortie = x × (1-wet) + courbe × wet
```

Le mélange maximal de la courbe non linéaire est donc 14 %. Cette valeur a été choisie
pour apporter une densité légère sans transformer l’étage en distorsion large bande.
À zéro, le processeur est contourné bit pour bit à la précision du tampon copié.

### 6.8 Clipper

Le clipper est une courbe douce `tanh`, suréchantillonnée ×4 :

```text
drive = 10^(drive_dB/20)
forme = tanh(x × drive) / drive
wet = min(0,7, drive_dB/12)
sortie = x × (1-wet) + forme × wet
```

Le drive va de 0 à 12 dB. La division par `drive` conserve la pente des petits signaux
proche de l’unité et évite l’ancienne remontée artificielle des fondamentales graves.
Après retour à `Fs`, une garde borne le signal dans `[-1, +1]`. Le plafond de
livraison reste toutefois la responsabilité du limiteur suivant.

### 6.9 Limiteur

- canaux liés par le maximum absolu de chaque image ;
- détection et traitement à `4 × Fs` ;
- plafond réglable à `0 dBFS` ou moins, interface : −6 à −0,1 dBFS ;
- lookahead : 0 à 10 ms, 3 ms par défaut ;
- release : 10 à 500 ms, 80 ms par défaut.

Le détecteur calcule le maximum futur sur l’horizon de lookahead. Le gain désiré est :

```text
min(1, plafond_linéaire / crête_future)
```

La réduction est instantanée. Le retour est exponentiel avec
`exp(-1/(release × Fs_interne))`. Un même gain est appliqué à tous les canaux.

Après retour à la fréquence source, OpenMaster suréchantillonne encore la sortie ×4
pour vérifier la crête reconstruite. Si elle dépasse le plafond, un gain lié global
ramène cette crête au plafond. Une dernière garde image par image absorbe les
dépassements numériques résiduels.

Le champ historique s’appelle `ceiling_dbfs`, mais la vérification reconstruite vise
bien une sécurité de type true peak estimé. La précision reste celle du
suréchantillonnage polyphasé ×4, pas celle d’un appareil certifié.

## 7. Export WAV

Le WAV est un PCM entier 16, 24 ou 32 bits, au sample rate de la source. La
quantification utilise :

```text
échelle = 2^(bits-1) - 1
entier = arrondi(limiter(signal, -1, +1) × échelle)
```

Le mastering active un dither TPDF déterministe par défaut. Deux suites pseudoaléatoires
initialisées avec la graine `0` sont soustraites, puis ajoutées avec une amplitude
d’un LSB avant l’arrondi. Le déterminisme permet de reproduire exactement un export
à source, version et réglages identiques.

L’écriture passe par un fichier temporaire dans le dossier cible, puis par un
remplacement atomique. Un rendu partiellement écrit n’est donc pas publié comme master
valide.

## 8. Paramètres fixes et réglables

| Contrôle public | Plage | Défaut moteur | Effet |
| --- | ---: | ---: | --- |
| Cible | −24 à −8 LUFS | −14 | Décision de gain |
| Correction maximale | 0 à 12 dB | 12 | Borne du gain |
| Plafond | −6 à −0,1 dBFS dans l’UI | −1 | Limiteur |
| EQ grave/médium/aigu | −6 à +6 dB | 0 | Peaking 100/1k/10k |
| Passe-haut | 15 à 80 Hz | 25 | Butterworth ordre 4 |
| EQ dynamique max | 0 à 12 dB | 0 | 2,5 kHz, Q 1 |
| Grave dynamique max | 0 à 12 dB | 0 | Sous 140 Hz |
| De-esser max | 0 à 12 dB | 0 | Autour de 7 kHz |
| Saturation | 0 à 1 | 0 | Mélange non linéaire |
| Clipper | 0 à 12 dB | 0 | Drive tanh |
| Lookahead | 0 à 10 ms | 3 | Horizon limiteur |
| Release | 10 à 500 ms | 80 | Retour limiteur |
| WAV | 16/24/32 bits | 24 | Quantification et dither |

Les fréquences, Q, ratios, attaques et releases des trois processeurs sélectifs ne
sont pas exposés par l’interface v3.3. Ils restent fixes pour rendre les presets
comparables et l’audit reproductible.

## 9. Presets livrés

Les presets sont des points de départ complets, pas une détection automatique du genre.
L’ordre des quatre valeurs « sélectif » est : EQ dynamique, grave dynamique, de-esser,
saturation.

| Preset | LUFS | Plafond | Corr. max | EQ bas/mid/haut | Sélectif | Clip | HPF | Limiteur | Bits |
| --- | ---: | ---: | ---: | --- | --- | ---: | ---: | --- | ---: |
| Transparent | −16 | −1,5 | 6 | 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 | 25 Hz | 3/80 ms | 24 |
| Streaming | −14 | −1 | 9 | 0 / 0 / 0 | 1,5 / 1,5 / 1,5 / 0,1 | 1 | 25 Hz | 3/80 ms | 24 |
| Podcast | −16 | −1 | 6 | −0,5 / +1 / +0,5 | 2 / 1 / 4 / 0,1 | 1 | 25 Hz | 3/80 ms | 16 |
| Rap | −10 | −1 | 10 | +0,5 / +0,5 / +0,75 | 0,5 / 2,5 / 1,5 / 0,04 | 1 | 25 Hz | 3/80 ms | 24 |
| Rap Reloaded | −10,5 | −1 | 6 | 0 / +0,25 / +0,25 | 0,5 / 0 / 0,5 / 0 | 0 | 20 Hz | 5/70 ms | 24 |
| Club | −10 | −0,5 | 10 | +0,5 / −0,5 / +1 | 2 / 5 / 2 / 0,08 | 3 | 25 Hz | 3/80 ms | 24 |
| Loud | −10 | −0,5 | 12 | +0,5 / 0 / +0,5 | 3 / 3 / 3 / 0,25 | 5 | 25 Hz | 3/80 ms | 24 |
| Dynamic | −18 | −2 | 5 | 0 / 0 / 0 | 0 / 0 / 0 / 0 | 0 | 25 Hz | 3/80 ms | 24 |

Tous activent le passe-haut et désactivent LamAI par défaut.

`Rap Reloaded` est volontairement distinct de `Rap`. Il ne compresse pas la bande
grave, ne sature pas et ne clippe pas. Son passe-haut à 20 Hz, sa correction limitée à
6 dB et son lookahead de 5 ms visent à protéger une 808 déjà dense. Son protocole de
mesure est détaillé dans [RAP_RELOADED.md](RAP_RELOADED.md).

## 10. Pré-écoute live contre rendu final

Le bouton **Original** envoie la source directement à la sortie. **Effets live**
utilise le même élément média et conserve la position de lecture.

La pré-écoute reproduit directement :

- les trois peaking EQ à 100 Hz/Q 0,7, 1 kHz/Q 1 et 10 kHz/Q 0,7 ;
- un passe-haut Web Audio à Q 0,707 ;
- le gain calculé depuis les LUFS analysés ;
- une approximation de la saturation et du clipper ;
- une limitation liée avec lookahead/release ;
- une audition quantifiée 16/24/32 bits.

Les changements sont lissés par `setTargetAtTime` avec une constante de 20 ms pour les
filtres et 10 ms pour la commutation Original/Live.

La pré-écoute ne simule pas l’EQ dynamique, le contrôle du grave et le de-esser. Un
ancien compresseur large bande faisait pomper les kicks et les 808 ; il est désormais
maintenu à seuil 0 dB et ratio 1:1. Les étages du navigateur ne sont pas
suréchantillonnés comme le moteur Python et l’implémentation du limiteur diffère.

Conséquence : la pré-écoute sert à décider, mais le WAV final et ses mesures sont
l’unique référence technique. Les contrôles sont étiquetés « live »,
« approximatif » ou « rendu requis » selon ce contrat.

## 11. LamAI et audit

Si LamAI est activé, OpenMaster lui envoie uniquement les mesures structurées et la
politique courante, jamais le son ni une URL MinIO. La politique courante est étiquetée
comme état de comparaison uniquement : LamAI doit choisir indépendamment chaque
contrôle ajustable et ne doit pas traiter le preset, sa cible LUFS ou sa correction
maximale comme des préférences à respecter. La réponse doit contenir exactement toutes
les clés de la politique. Toute clé absente, inconnue, non numérique ou hors borne
invalide la proposition entière.

Les centres, crossovers et seuils internes non exposés restent obligatoirement
identiques à la politique initiale. Cette validation serveur préserve la même topologie
sur les chemins local et RunPod. L’instruction interdit également d’inventer un genre,
une distorsion ou un déséquilibre spectral absent des mesures ; « meilleur » désigne
donc la meilleure décision défendable à partir des informations disponibles, pas une
promesse subjective d’écoute par le modèle.

La température demandée est `0,1`, la sortie est limitée à 900 tokens et doit être un
objet JSON. Même valide, la proposition repasse par les constructeurs et validations
du moteur. En cas d’indisponibilité ou de réponse invalide, OpenMaster rend avec la
politique déterministe initiale et l’indique dans le bloc d’audit.

L’audit de rendu conserve notamment :

- politique demandée et réglages effectifs ;
- gain demandé, gain borné et marge de crête informative ;
- raison de la décision ;
- proposition LamAI appliquée ou refusée, modèle et justification ;
- ordre des processeurs ;
- LUFS et true peak de sortie ;
- passes de calibration et erreur finale ;
- profondeur et application du dither ;
- empreinte SHA-256 de la source pour le chemin RunPod.

## 12. Reproductibilité et limites d’écoute

À version logicielle, source binaire et politique identiques, le chemin CPU donne le
même résultat, dither compris. Le worker local et le worker RunPod construisent le même
`MasteringPolicy` et utilisent le même `AutomaticMasteringService`.

Limites importantes :

- une source déjà écrêtée ne peut pas retrouver ses transitoires perdus ;
- une cible très forte peut respecter le plafond tout en produisant une réduction
  audible et une erreur LUFS résiduelle ;
- le limiteur lié protège l’image stéréo mais peut faire réagir les deux canaux à une
  crête présente sur un seul ;
- le ×4 réduit les erreurs inter-échantillons sans constituer une preuve absolue pour
  tous les codecs ou convertisseurs ;
- le passe-haut et l’EQ tonale sont causaux et modifient donc la phase ;
- les estimations LUFS, true peak, BPM et tonalité doivent être recoupées par les outils
  de livraison exigés par le diffuseur ;
- un preset n’est pas une promesse de qualité : balance, distorsion et dynamique
  doivent être validées à l’écoute, idéalement en comparaison à niveau perçu égal.

Pour un test significatif, fournir de préférence un premaster sans clipping, sans
limiteur de maximisation sur le bus, en WAV 24 ou 32 bits, au sample rate de la
session. Conserver quelques décibels de marge facilite le travail du limiteur, mais
OpenMaster n’exige pas une valeur de headroom arbitraire pour calculer le gain.

## 13. Emplacements du code faisant autorité

- analyse : `packages/analysis_engine/metrics.py` ;
- décision et convergence : `packages/dsp_engine/automatic.py` ;
- ordre de chaîne : `packages/dsp_engine/mastering.py` ;
- EQ : `packages/dsp_engine/equalizer.py` ;
- traitements sélectifs : `packages/dsp_engine/spectral_dynamics.py` ;
- saturation, clipper, limiteur : fichiers homonymes de `packages/dsp_engine/` ;
- export PCM/dither : `packages/audio_core/wav_encoder.py` ;
- presets : `apps/web/src/masteringPresets.ts` ;
- pré-écoute : `apps/web/src/components/InteractivePreview.vue` et
  `apps/web/public/mastering-preview-worklet.js` ;
- conseil LamAI : `packages/ai_mastering/client.py`.
