<script setup lang="ts">
import type { Locale } from "../i18n";

defineProps<{ locale: Locale }>();
defineEmits<{ back: [] }>();
</script>

<template>
  <main v-if="locale === 'en'" class="guide-page">
    <header class="guide-hero">
      <p class="eyebrow">OpenMaster field guide</p>
      <h1>Read the sound.<br /><em>Shape the master.</em></h1>
      <p>Everything shown by the studio, what each control changes, and how a track moves through the pipeline.</p>
      <button type="button" @click="$emit('back')">← Return to studio</button>
    </header>
    <nav class="guide-index"><a href="#pipeline">Pipeline</a><a href="#measurements">Measurements</a><a href="#controls">Controls</a><a href="#comparisons">Comparisons</a><a href="#delivery">Delivery</a></nav>
    <section id="pipeline" class="guide-section">
      <p class="eyebrow">01 · Pipeline</p><h2>From source to master</h2>
      <div class="guide-steps">
        <article><b>1</b><h3>Upload</h3><p>The source is validated and stored privately in MinIO.</p></article>
        <article><b>2</b><h3>Analysis</h3><p>OpenMaster decodes the audio and measures levels, dynamics, stereo and spectral identity.</p></article>
        <article><b>3</b><h3>Decision</h3><p>The assistant derives a bounded gain decision from your policy and measured headroom.</p></article>
        <article><b>4</b><h3>Render</h3><p>High-pass, selective dynamics, saturation, clipping, True Peak limiting, output measurement and dither run locally or on RunPod.</p></article>
        <article><b>5</b><h3>Delivery</h3><p>A private WAV is published through a short-lived signed download.</p></article>
      </div>
    </section>
    <section id="measurements" class="guide-section">
      <p class="eyebrow">02 · Measurements</p><h2>How to read the analysis</h2>
      <div class="glossary">
        <article><h3>Integrated LUFS</h3><p>Loudness Units relative to Full Scale estimate perceived average loudness across the complete programme. More negative means quieter: −16 LUFS is quieter and usually more dynamic than −9 LUFS.</p></article>
        <article><h3>RMS</h3><p>Average signal energy. It helps describe density but does not model perception like LUFS.</p></article>
        <article><h3>Sample & true peak</h3><p>Sample peak reads stored samples; true peak estimates peaks created between samples during conversion.</p></article>
        <article><h3>Dynamic range</h3><p>Difference between quieter and louder programme windows. Larger values generally mean more macro contrast.</p></article>
        <article><h3>Crest factor</h3><p>Difference between RMS and peak. It indicates transient contrast, not musical quality.</p></article>
        <article><h3>Stereo width</h3><p>Ratio of side to mid energy. A wide value is neither automatically better nor safer.</p></article>
        <article><h3>Phase correlation</h3><p>Negative values warn that stereo content may cancel when folded to mono.</p></article>
        <article><h3>Spectral centroid</h3><p>The brightness center of gravity. It is one summary value, not a complete spectrum.</p></article>
        <article><h3>BPM & key</h3><p>Deterministic estimates useful for context; complex or changing music can reduce accuracy.</p></article>
      </div>
      <aside class="lufs-explainer">
        <div><span>−18</span><small>Dynamic</small></div><i></i><div><span>−16</span><small>Natural</small></div><i></i><div><span>−14</span><small>Streaming start</small></div><i></i><div><span>−9</span><small>Loud</small></div>
        <p><strong>LUFS is not a volume knob guarantee.</strong> OpenMaster measures integrated LUFS with perceptual weighting and silence gating, then requests the gain needed to approach your target. If that gain would cross the configured peak ceiling, safety wins and the target may not be reached. Streaming platforms can normalize playback, so louder masters do not necessarily play louder to listeners.</p>
      </aside>
    </section>
    <section id="controls" class="guide-section">
      <p class="eyebrow">03 · Controls</p><h2>What your settings change</h2>
      <div class="control-guide">
        <article><span>LUFS</span><div><h3>Loudness target</h3><p>Requests a gain change toward the chosen programme loudness. Peak safety may prevent reaching it exactly.</p></div></article>
        <article><span>dBFS</span><div><h3>Limiter ceiling</h3><p>Sets the maximum linked sample peak. Lower values preserve more output headroom.</p></div></article>
        <article><span>±dB</span><div><h3>Maximum correction</h3><p>Caps how far automatic gain may move in either direction, protecting against extreme decisions.</p></div></article>
        <article><span>EQ</span><div><h3>Three-band equalizer</h3><p>Applies bounded corrections around 100 Hz, 1 kHz and 10 kHz before gain and dynamics.</p></div></article>
        <article><span>HPF</span><div><h3>High-pass and selective dynamics</h3><p>The high-pass removes subsonic energy; dynamic EQ, bass control and de-essing attenuate only their frequency regions when triggered.</p></div></article>
        <article><span>SAT</span><div><h3>Light saturation</h3><p>Adds bounded oversampled harmonic density before transient clipping.</p></div></article>
        <article><span>×4</span><div><h3>Soft clipper</h3><p>Rounds short peaks at four times the sample rate. More drive creates density but can reduce punch.</p></div></article>
        <article><span>ms</span><div><h3>Lookahead and release</h3><p>Lookahead anticipates peaks; release controls how quickly limiter gain returns afterward.</p></div></article>
        <article><span>PCM</span><div><h3>WAV depth</h3><p>16 bit is compact delivery, 24 bit is the normal production choice, and 32 bit preserves additional integer resolution.</p></div></article>
      </div>
      <aside class="guide-callout"><strong>What OpenMaster does not hide</strong><p>The active path is explicit: high-pass, tonal and dynamic EQ, bass control, de-essing, gain, saturation, clipping, True Peak limiting, output measurement and dither. Zero-strength stages are true bypasses.</p></aside>
    </section>
    <section id="comparisons" class="guide-section">
      <p class="eyebrow">04 · Comparisons</p><h2>Understand the interactive graphs</h2>
      <div class="glossary">
        <article><h3>Peak envelope</h3><p>Shows peak amplitude relative to digital full scale through time. The slider interpolates every point between the original and mastered envelopes, so the geometry visibly evolves.</p></article>
        <article><h3>Peak density</h3><p>A moving RMS calculation over the compact envelope. It reveals sustained dense passages but is not the audio signal RMS measurement.</p></article>
        <article><h3>Transient activity</h3><p>Shows point-to-point envelope variation. It helps locate rhythmic change, but it is neither a transient detector nor a spectrum.</p></article>
        <article><h3>Spectral balance</h3><p>Shows averaged RMS energy on logarithmic frequencies from 40 Hz to 20 kHz. Its fixed −100 to 0 dBFS scale preserves real before/after differences.</p></article>
        <article><h3>Windowed level</h3><p>Shows RMS energy through time on a fixed −60 to 0 dBFS scale. It is deliberately labelled RMS and must not be read as integrated LUFS.</p></article>
      </div>
      <aside class="guide-callout"><strong>How the sliders work</strong><p>At 0% the active curve is the original; at 100% it is the master. Intermediate positions interpolate the real stored measurements point by point. Faint reference lines keep both endpoints visible.</p></aside>
    </section>
    <section id="delivery" class="guide-section">
      <p class="eyebrow">05 · Delivery</p><h2>Practical starting points</h2>
      <div class="delivery-table">
        <div><strong>Transparent</strong><span>−16 LUFS</span><span>−1.5 dBFS</span><span>±6 dB</span></div>
        <div><strong>Streaming</strong><span>−14 LUFS</span><span>−1.0 dBFS</span><span>±9 dB</span></div>
        <div><strong>Rap</strong><span>−10 LUFS</span><span>−0.8 dBFS</span><span>±9 dB</span></div>
        <div><strong>Loud</strong><span>−9 LUFS</span><span>−0.5 dBFS</span><span>±12 dB</span></div>
        <div><strong>Podcast</strong><span>−16 LUFS</span><span>−1.0 dBFS</span><span>±6 dB</span></div>
      </div>
      <p class="guide-footnote">These are starting policies, not platform compliance guarantees. Always listen to the output and compare it at matched loudness.</p>
    </section>
  </main>

  <main v-else class="guide-page">
    <header class="guide-hero">
      <p class="eyebrow">Guide pratique OpenMaster</p>
      <h1>Lire le son.<br /><em>Façonner le master.</em></h1>
      <p>Comprendre toutes les informations du studio, l’effet de chaque réglage et le parcours complet d’un morceau.</p>
      <button type="button" @click="$emit('back')">← Retour au studio</button>
    </header>
    <nav class="guide-index"><a href="#pipeline-fr">Chaîne</a><a href="#mesures-fr">Mesures</a><a href="#reglages-fr">Réglages</a><a href="#comparaisons-fr">Comparaisons</a><a href="#livraison-fr">Livraison</a></nav>
    <section id="pipeline-fr" class="guide-section">
      <p class="eyebrow">01 · Chaîne de traitement</p><h2>De la source au master</h2>
      <div class="guide-steps">
        <article><b>1</b><h3>Envoi</h3><p>La source est validée puis stockée de manière privée dans MinIO.</p></article>
        <article><b>2</b><h3>Analyse</h3><p>OpenMaster décode le son et mesure les niveaux, la dynamique, la stéréo et l’identité spectrale.</p></article>
        <article><b>3</b><h3>Décision</h3><p>L’assistant détermine une correction de gain bornée à partir de votre politique et de la marge mesurée.</p></article>
        <article><b>4</b><h3>Rendu</h3><p>Coupe-bas, dynamique sélective, saturation, clipping, limitation True Peak, mesure de sortie et dither s’exécutent localement ou sur RunPod.</p></article>
        <article><b>5</b><h3>Livraison</h3><p>Un WAV privé est publié au moyen d’un téléchargement signé de courte durée.</p></article>
      </div>
    </section>
    <section id="mesures-fr" class="guide-section">
      <p class="eyebrow">02 · Mesures</p><h2>Lire correctement l’analyse</h2>
      <div class="glossary">
        <article><h3>LUFS intégré</h3><p>Les unités de niveau sonore relatif à la pleine échelle estiment le niveau moyen perçu sur tout le programme. Une valeur plus négative est plus faible : −16 LUFS est moins fort et souvent plus dynamique que −9 LUFS.</p></article>
        <article><h3>RMS</h3><p>Énergie moyenne du signal. Elle décrit sa densité, mais ne modélise pas la perception comme les LUFS.</p></article>
        <article><h3>Crête et crête vraie</h3><p>La crête lit les échantillons stockés ; la crête vraie estime les dépassements créés entre les échantillons pendant une conversion.</p></article>
        <article><h3>Étendue dynamique</h3><p>Écart entre les fenêtres calmes et fortes du programme. Une valeur élevée indique généralement davantage de contraste global.</p></article>
        <article><h3>Facteur de crête</h3><p>Écart entre le RMS et la crête. Il renseigne sur le contraste transitoire, pas sur la qualité musicale.</p></article>
        <article><h3>Largeur stéréo</h3><p>Rapport entre l’énergie latérale et centrale. Une valeur large n’est pas automatiquement meilleure ni plus sûre.</p></article>
        <article><h3>Corrélation de phase</h3><p>Une valeur négative avertit que des éléments stéréo peuvent s’annuler lors du passage en mono.</p></article>
        <article><h3>Centroïde spectral</h3><p>Centre de gravité de la brillance. C’est une valeur synthétique, pas un spectre complet.</p></article>
        <article><h3>BPM et tonalité</h3><p>Estimations déterministes utiles au contexte ; une musique complexe ou évolutive peut réduire leur précision.</p></article>
      </div>
      <aside class="lufs-explainer">
        <div><span>−18</span><small>Dynamique</small></div><i></i><div><span>−16</span><small>Naturel</small></div><i></i><div><span>−14</span><small>Départ streaming</small></div><i></i><div><span>−9</span><small>Fort</small></div>
        <p><strong>Les LUFS ne garantissent pas un volume de lecture.</strong> OpenMaster mesure les LUFS intégrés avec une pondération perceptuelle et un seuil excluant les silences, puis demande le gain nécessaire pour approcher la cible. Si ce gain dépasse le plafond de crête configuré, la sécurité est prioritaire et la cible peut ne pas être atteinte. Les plateformes peuvent normaliser la lecture : un master plus fort ne sera donc pas nécessairement entendu plus fort.</p>
      </aside>
    </section>
    <section id="reglages-fr" class="guide-section">
      <p class="eyebrow">03 · Réglages</p><h2>Ce que modifient vos paramètres</h2>
      <div class="control-guide">
        <article><span>LUFS</span><div><h3>Niveau sonore cible</h3><p>Demande une correction vers le niveau global choisi. La protection des crêtes peut empêcher de l’atteindre exactement.</p></div></article>
        <article><span>dBFS</span><div><h3>Plafond du limiteur</h3><p>Définit la crête d’échantillon liée maximale. Une valeur plus basse conserve davantage de marge en sortie.</p></div></article>
        <article><span>±dB</span><div><h3>Correction maximale</h3><p>Limite le déplacement automatique du gain dans les deux directions afin d’éviter les décisions extrêmes.</p></div></article>
        <article><span>EQ</span><div><h3>Égaliseur trois bandes</h3><p>Applique des corrections bornées autour de 100 Hz, 1 kHz et 10 kHz avant le gain et la dynamique.</p></div></article>
        <article><span>HPF</span><div><h3>Coupe-bas et dynamique sélective</h3><p>Le coupe-bas retire l’infragrave ; l’EQ dynamique, le contrôle du grave et le de-esser n’atténuent leur zone que lorsqu’elle déclenche le détecteur.</p></div></article>
        <article><span>SAT</span><div><h3>Saturation légère</h3><p>Ajoute une densité harmonique bornée et suréchantillonnée avant le traitement des crêtes.</p></div></article>
        <article><span>×4</span><div><h3>Clipper doux</h3><p>Arrondit les crêtes courtes à quatre fois la fréquence d’échantillonnage. Un drive élevé densifie le son mais peut réduire l’impact.</p></div></article>
        <article><span>ms</span><div><h3>Anticipation et relâchement</h3><p>L’anticipation prépare les crêtes ; le relâchement règle la vitesse de retour du gain du limiteur.</p></div></article>
        <article><span>PCM</span><div><h3>Résolution WAV</h3><p>16 bits est compact pour la livraison, 24 bits est le choix normal de production et 32 bits conserve une résolution entière supplémentaire.</p></div></article>
      </div>
      <aside class="guide-callout"><strong>Ce qu’OpenMaster ne cache pas</strong><p>La chaîne est explicite : coupe-bas, EQ tonale et dynamique, contrôle du grave, de-esser, gain, saturation, clipper, limiteur True Peak, mesure de sortie et dither. Un étage réglé à zéro est réellement contourné.</p></aside>
    </section>
    <section id="comparaisons-fr" class="guide-section">
      <p class="eyebrow">04 · Comparaisons</p><h2>Comprendre les graphiques interactifs</h2>
      <div class="glossary">
        <article><h3>Enveloppe de crête</h3><p>Affiche l’amplitude des crêtes par rapport à la pleine échelle numérique. Le curseur interpole chaque point entre les enveloppes originale et masterisée : la géométrie évolue donc visiblement.</p></article>
        <article><h3>Densité des crêtes</h3><p>Calcul RMS glissant appliqué à l’enveloppe compacte. Il révèle les passages durablement denses, mais ne remplace pas la mesure RMS du signal audio.</p></article>
        <article><h3>Activité transitoire</h3><p>Affiche la variation entre les points de l’enveloppe. Elle aide à localiser les changements rythmiques, mais ne constitue ni un détecteur de transitoires ni un spectre.</p></article>
        <article><h3>Équilibre spectral</h3><p>Affiche l’énergie RMS moyenne sur des fréquences logarithmiques de 40 Hz à 20 kHz. Son échelle fixe de −100 à 0 dBFS préserve les différences réelles avant/après.</p></article>
        <article><h3>Niveau par fenêtre</h3><p>Affiche l’énergie RMS dans le temps sur une échelle fixe de −60 à 0 dBFS. Cette vue est explicitement un RMS et ne doit pas être lue comme des LUFS intégrés.</p></article>
      </div>
      <aside class="guide-callout"><strong>Fonctionnement des curseurs</strong><p>À 0 %, la courbe active est l’original ; à 100 %, elle correspond au master. Les positions intermédiaires interpolent point par point les mesures réellement enregistrées. Les lignes discrètes conservent les deux références visibles.</p></aside>
    </section>
    <section id="livraison-fr" class="guide-section">
      <p class="eyebrow">05 · Livraison</p><h2>Points de départ pratiques</h2>
      <div class="delivery-table">
        <div><strong>Transparent</strong><span>−16 LUFS</span><span>−1,5 dBFS</span><span>±6 dB</span></div>
        <div><strong>Streaming</strong><span>−14 LUFS</span><span>−1,0 dBFS</span><span>±9 dB</span></div>
        <div><strong>Rap</strong><span>−10 LUFS</span><span>−0,8 dBFS</span><span>±9 dB</span></div>
        <div><strong>Puissant</strong><span>−9 LUFS</span><span>−0,5 dBFS</span><span>±12 dB</span></div>
        <div><strong>Podcast</strong><span>−16 LUFS</span><span>−1,0 dBFS</span><span>±6 dB</span></div>
      </div>
      <p class="guide-footnote">Ces valeurs sont des politiques de départ, pas des garanties de conformité à une plateforme. Écoutez toujours le résultat et comparez-le à niveau sonore perçu égal.</p>
    </section>
  </main>
</template>
