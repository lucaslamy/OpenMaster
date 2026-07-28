<script setup lang="ts">
import { computed } from "vue";

import type { Locale } from "../i18n";

const props = defineProps<{ locale: Locale }>();
defineEmits<{ back: []; studio: [] }>();

const c = (fr: string, en: string) => props.locale === "fr" ? fr : en;

const stages = computed(() => [
  ["HPF", c("Passe-haut", "High-pass"), "24 dB/oct · 15–80 Hz"],
  ["EQ", c("EQ tonale", "Tonal EQ"), "100 Hz · 1 kHz · 10 kHz"],
  ["DYN", c("Dynamique sélective", "Selective dynamics"), "2.5 kHz · <140 Hz · 7 kHz"],
  ["GAIN", c("Gain LUFS", "LUFS gain"), "T − L · ±M"],
  ["SAT", c("Saturation", "Saturation"), "tanh · ×4"],
  ["CLIP", c("Clipper doux", "Soft clipper"), "tanh · ×4"],
  ["LIMIT", c("Limiteur lié", "Linked limiter"), "lookahead · ×4"],
  ["PCM", c("Export WAV", "WAV export"), "16 · 24 · 32 bit"],
]);

const selective = computed(() => [
  {
    name: c("Égaliseur dynamique", "Dynamic equalizer"),
    band: "2.5 kHz · Q 1",
    detector: "−18 dBFS · 2:1",
    timing: "12 / 120 ms",
  },
  {
    name: c("Contrôle du grave", "Bass control"),
    band: "< 140 Hz",
    detector: "−16 dBFS · 3:1",
    timing: "25 / 180 ms",
  },
  {
    name: "De-esser",
    band: "7 kHz · Q 1.4",
    detector: "−22 dBFS · 4:1",
    timing: "2 / 70 ms",
  },
]);

const presets = [
  ["Transparent", "−16", "−1.5", "6", "0 / 0 / 0", "0", "3 / 80"],
  ["Streaming", "−14", "−1", "9", "0 / 0 / 0", "1", "3 / 80"],
  ["Podcast", "−16", "−1", "6", "−0.5 / +1 / +0.5", "1", "3 / 80"],
  ["Rap", "−10", "−1", "10", "+0.5 / +0.5 / +0.75", "1", "3 / 80"],
  ["Rap Reloaded", "−10.5", "−1", "6", "0 / +0.25 / +0.25", "0", "5 / 70"],
  ["Club", "−10", "−0.5", "10", "+0.5 / −0.5 / +1", "3", "3 / 80"],
  ["Loud", "−10", "−0.5", "12", "+0.5 / 0 / +0.5", "5", "3 / 80"],
  ["Dynamic", "−18", "−2", "5", "0 / 0 / 0", "0", "3 / 80"],
];
</script>

<template>
  <main class="technical-page">
    <header class="technical-hero">
      <div>
        <p class="eyebrow">{{ c("Référence ingénieur son · moteur 3.4", "Sound engineer reference · engine 3.4") }}</p>
        <h1>{{ c("Dans le moteur.", "Inside the engine.") }}<br /><em>{{ c("Sans boîte noire.", "No black box.") }}</em></h1>
        <p>
          {{ c(
            "La chaîne exacte, ses constantes, ses détecteurs et ses limites. Chaque schéma ci-dessous représente le code réellement exécuté par le rendu final.",
            "The exact chain, constants, detectors, and limits. Every diagram below represents code actually executed by the final renderer.",
          ) }}
        </p>
        <div class="guide-actions">
          <button type="button" @click="$emit('studio')">← {{ c("Ouvrir le studio", "Open studio") }}</button>
          <a
            href="https://github.com/lucaslamy/OpenMaster/blob/main/docs/MASTERING_TECHNICAL_REFERENCE.fr.md"
            target="_blank"
            rel="noopener noreferrer"
          >{{ c("Version GitHub exhaustive", "Complete GitHub reference") }} ↗</a>
        </div>
      </div>
      <div class="technical-hero-visual" aria-hidden="true">
        <div class="tech-disc">
          <i></i><i></i><i></i>
          <span>FLOAT64</span>
        </div>
        <div class="tech-meter">
          <b v-for="height in [18, 36, 58, 84, 67, 44, 72, 91, 63, 32, 52, 76]" :key="height" :style="{ height: `${height}%` }"></b>
        </div>
      </div>
    </header>

    <nav class="technical-index" :aria-label="c('Sections techniques', 'Technical sections')">
      <a href="#signal">{{ c("Signal", "Signal") }}</a>
      <a href="#measure">{{ c("Mesures", "Measurements") }}</a>
      <a href="#dynamics">{{ c("Dynamique", "Dynamics") }}</a>
      <a href="#peaks">{{ c("Crêtes", "Peaks") }}</a>
      <a href="#ai">LamAI</a>
      <a href="#presets">Presets</a>
      <a href="#delivery">{{ c("Livraison", "Delivery") }}</a>
    </nav>

    <section id="signal" class="technical-section">
      <div class="technical-heading">
        <p class="eyebrow">01 · {{ c("Ordre du signal", "Signal order") }}</p>
        <h2>{{ c("Une chaîne fixe, un résultat reproductible", "A fixed chain, a reproducible result") }}</h2>
        <p>{{ c(
          "Le preset ne change jamais l’ordre des étages. Il ne fournit que des valeurs explicites à cette architecture.",
          "A preset never changes processor order. It only supplies explicit values to this architecture.",
        ) }}</p>
      </div>
      <div class="tech-signal-chain">
        <article v-for="(stage, index) in stages" :key="stage[0]" :style="{ '--stage-index': index }">
          <small>{{ stage[0] }}</small>
          <strong>{{ stage[1] }}</strong>
          <span>{{ stage[2] }}</span>
          <i v-if="index < stages.length - 1">→</i>
        </article>
      </div>
      <div class="technical-facts">
        <article><span>64</span><p><strong>float64</strong>{{ c(" en interne, forme (frames, canaux)", " internally, shape (frames, channels)") }}</p></article>
        <article><span>=</span><p><strong>{{ c("Fréquence source", "Source sample rate") }}</strong>{{ c(" conservée hors ×4 interne", " retained outside internal ×4") }}</p></article>
        <article><span>↔</span><p><strong>{{ c("Canaux liés", "Linked channels") }}</strong>{{ c(" pour les détecteurs dynamiques", " for dynamic detectors") }}</p></article>
      </div>
    </section>

    <section id="measure" class="technical-section technical-split">
      <div class="technical-heading">
        <p class="eyebrow">02 · {{ c("Analyse", "Analysis") }}</p>
        <h2>{{ c("Ce que le moteur mesure avant de décider", "What the engine measures before deciding") }}</h2>
        <p>{{ c(
          "Les décisions partent de mesures déterministes, pas d’une étiquette de genre. BPM et tonalité restent informatifs et ne pilotent aucun processeur.",
          "Decisions start from deterministic measurements, not a genre label. BPM and key remain informative and drive no processor.",
        ) }}</p>
      </div>
      <div class="loudness-diagram panel">
        <header><strong>{{ c("LUFS intégré", "Integrated LUFS") }}</strong><span>400 ms · hop 100 ms</span></header>
        <div class="gate-bars" aria-hidden="true">
          <i v-for="(height, index) in [22, 33, 14, 54, 67, 38, 76, 82, 43, 62, 89, 71, 35, 78, 94, 58]" :key="index" :style="{ height: `${height}%`, '--bar-index': index }"></i>
          <b class="absolute-gate">−70</b>
          <b class="relative-gate">−10 LU</b>
        </div>
        <footer>
          <span>K shelf 1681.974 Hz · +4 dB</span>
          <span>HPF 38.135 Hz · order 2</span>
        </footer>
      </div>
      <div class="measurement-grid">
        <article><small>RMS</small><code>20 log10(√mean(x²))</code></article>
        <article><small>Sample peak</small><code>20 log10(max |x|)</code></article>
        <article><small>True peak</small><code>resample_poly(x, 4, 1)</code></article>
        <article><small>Crest factor</small><code>peak dBFS − RMS dBFS</code></article>
        <article><small>{{ c("Dynamique", "Dynamic range") }}</small><code>P95(RMS₄₀₀) − P10(RMS₄₀₀)</code></article>
        <article><small>{{ c("Largeur", "Stereo width") }}</small><code>RMS(Side) / RMS(Mid)</code></article>
      </div>
    </section>

    <section id="dynamics" class="technical-section">
      <div class="technical-heading">
        <p class="eyebrow">03 · {{ c("Dynamique spectrale", "Spectral dynamics") }}</p>
        <h2>{{ c("Atténuer une zone sans pomper tout le mix", "Attenuate one region without pumping the mix") }}</h2>
        <p>{{ c(
          "Le maximum absolu de tous les canaux pilote une enveloppe commune. La balance stéréo reste intacte pendant la réduction.",
          "The absolute maximum across all channels drives one shared envelope. Stereo balance remains intact during reduction.",
        ) }}</p>
      </div>
      <div class="linked-detector">
        <div class="detector-input">
          <span>L</span><i></i><i></i><i></i>
          <span>R</span><i></i><i></i><i></i>
        </div>
        <div class="detector-core"><small>MAX |x|</small><strong>LINK</strong><b></b></div>
        <div class="detector-output"><span>GAIN</span><i></i><span>L + R</span></div>
      </div>
      <div class="selective-grid">
        <article v-for="processor in selective" :key="processor.name">
          <div class="band-orbit" aria-hidden="true"><i></i><b></b></div>
          <h3>{{ processor.name }}</h3>
          <dl>
            <div><dt>{{ c("Bande", "Band") }}</dt><dd>{{ processor.band }}</dd></div>
            <div><dt>{{ c("Détecteur", "Detector") }}</dt><dd>{{ processor.detector }}</dd></div>
            <div><dt>A / R</dt><dd>{{ processor.timing }}</dd></div>
          </dl>
        </article>
      </div>
      <code class="formula-block">reduction = min(maxReduction, max(0, detector − threshold) × (1 − 1/ratio))</code>
    </section>

    <section id="peaks" class="technical-section">
      <div class="technical-heading">
        <p class="eyebrow">04 · {{ c("Densité et crêtes", "Density and peaks") }}</p>
        <h2>{{ c("Trois étages, trois responsabilités", "Three stages, three responsibilities") }}</h2>
      </div>
      <div class="peak-processors">
        <article>
          <div class="transfer-curve">
            <svg viewBox="0 0 180 120" role="img" :aria-label="c('Courbe de saturation tanh', 'tanh saturation curve')">
              <path d="M10 110 C55 109 60 72 90 60 C120 48 125 11 170 10" />
              <line x1="10" y1="110" x2="170" y2="10" />
            </svg>
          </div>
          <small>SATURATION</small><h3>wet = 0.14 × amount</h3>
          <p>drive = 1 + 0.75 × amount · tanh · ×4</p>
        </article>
        <article>
          <div class="clip-wave" aria-hidden="true"><i></i><b></b></div>
          <small>SOFT CLIPPER</small><h3>wet = min(0.7, drive/12)</h3>
          <p>tanh(x × drive) / drive · 0–12 dB · ×4</p>
        </article>
        <article>
          <div class="lookahead-visual" aria-hidden="true">
            <i class="incoming-peak"></i><i class="lookahead-window"></i><b class="gain-envelope"></b>
          </div>
          <small>TRUE-PEAK LIMITER</small><h3>0–10 ms · 10–500 ms</h3>
          <p>{{ c("maximum futur, release exponentiel, garde reconstruite ×4", "future maximum, exponential release, reconstructed ×4 guard") }}</p>
        </article>
      </div>
      <aside class="technical-warning">
        <strong>{{ c("Ce que le limiteur ne peut pas faire", "What the limiter cannot do") }}</strong>
        <p>{{ c(
          "Il protège le plafond mais ne recrée pas les transitoires déjà écrêtés dans la source. Une cible forte peut être sûre numériquement et néanmoins trop dense musicalement.",
          "It protects the ceiling but cannot restore transients already clipped in the source. A loud target can be numerically safe yet musically too dense.",
        ) }}</p>
      </aside>
    </section>

    <section id="ai" class="technical-section">
      <div class="technical-heading">
        <p class="eyebrow">05 · LamAI</p>
        <h2>{{ c("L’IA conseille. Le DSP garde l’autorité.", "AI advises. DSP stays authoritative.") }}</h2>
        <p>{{ c(
          "Le son, les URL MinIO et les secrets ne quittent jamais OpenMaster. LamAI reçoit uniquement les mesures et un état avant destiné à l’audit.",
          "Audio, MinIO URLs, and secrets never leave OpenMaster. LamAI receives measurements and a before-state used only for audit.",
        ) }}</p>
      </div>
      <div class="ai-boundary-diagram">
        <article><span>01</span><strong>{{ c("Mesures", "Measurements") }}</strong><small>LUFS · peak · DR · crest · stereo</small></article>
        <i>→</i>
        <article class="ai-node"><span>02</span><strong>LamAI</strong><small>{{ c("politique indépendante bornée", "bounded independent policy") }}</small></article>
        <i>→</i>
        <article><span>03</span><strong>VALIDATION</strong><small>{{ c("clés · types · bornes · topologie", "keys · types · bounds · topology") }}</small></article>
        <i>→</i>
        <article><span>04</span><strong>DSP</strong><small>{{ c("rendu déterministe", "deterministic render") }}</small></article>
      </div>
      <div class="ai-contract-grid">
        <article><b>✓</b><p>{{ c("Tous les contrôles ajustables peuvent remplacer le preset.", "Every adjustable control may replace the preset.") }}</p></article>
        <article><b>×</b><p>{{ c("Les centres et seuils internes restent verrouillés.", "Internal centers and thresholds remain locked.") }}</p></article>
        <article><b>↺</b><p>{{ c("Toute réponse invalide déclenche le repli déterministe.", "Any invalid response triggers deterministic fallback.") }}</p></article>
      </div>
    </section>

    <section id="presets" class="technical-section">
      <div class="technical-heading">
        <p class="eyebrow">06 · Presets</p>
        <h2>{{ c("Des points de départ, jamais des promesses", "Starting points, never promises") }}</h2>
      </div>
      <div class="preset-reference">
        <table>
          <thead><tr><th>Preset</th><th>LUFS</th><th>dBTP</th><th>± dB</th><th>EQ 100/1k/10k</th><th>Clip</th><th>L / R ms</th></tr></thead>
          <tbody>
            <tr v-for="preset in presets" :key="preset[0]">
              <td>{{ preset[0] }}</td>
              <td
                v-for="(value, valueIndex) in preset.slice(1)"
                :key="`${preset[0]}-${valueIndex}`"
              >{{ value }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p class="technical-caption">{{ c(
        "Rap Reloaded : HPF 20 Hz, dynamique 0.5 / 0 / 0.5 dB, saturation 0. Les autres presets utilisent un HPF 25 Hz.",
        "Rap Reloaded: 20 Hz HPF, selective dynamics 0.5 / 0 / 0.5 dB, saturation 0. Other presets use a 25 Hz HPF.",
      ) }}</p>
    </section>

    <section id="delivery" class="technical-section">
      <div class="technical-heading">
        <p class="eyebrow">07 · {{ c("Préécoute et livraison", "Preview and delivery") }}</p>
        <h2>{{ c("Entendre vite, rendre exactement", "Hear quickly, render exactly") }}</h2>
      </div>
      <div class="preview-final">
        <article>
          <span>WEB AUDIO</span><h3>{{ c("Préécoute locale", "Local preview") }}</h3>
          <ul>
            <li>EQ 100 Hz / 1 kHz / 10 kHz</li>
            <li>{{ c("Passe-haut navigateur", "Browser high-pass") }}</li>
            <li>{{ c("Gain LUFS approximatif", "Approximate LUFS gain") }}</li>
            <li>{{ c("Saturation, clipper, limiteur approchés", "Approximate saturation, clipper, limiter") }}</li>
          </ul>
        </article>
        <div class="render-divider"><i></i><strong>≠</strong><i></i></div>
        <article>
          <span>PYTHON FLOAT64</span><h3>{{ c("WAV final", "Final WAV") }}</h3>
          <ul>
            <li>{{ c("Chaîne complète neuf étages", "Complete nine-stage chain") }}</li>
            <li>{{ c("Dynamique sélective réelle", "Real selective dynamics") }}</li>
            <li>{{ c("Suréchantillonnage polyphasé ×4", "Polyphase ×4 oversampling") }}</li>
            <li>{{ c("Mesure après limiteur et calibration", "Post-limiter measurement and calibration") }}</li>
          </ul>
        </article>
      </div>
      <div class="export-strip">
        <div><small>PCM</small><strong>16 / 24 / 32 bit</strong></div>
        <div><small>DITHER</small><strong>TPDF · seed 0 · 1 LSB</strong></div>
        <div><small>WRITE</small><strong>{{ c("temporaire → atomique", "temporary → atomic") }}</strong></div>
      </div>
      <aside class="technical-warning">
        <strong>{{ c("Contrôle de livraison", "Delivery control") }}</strong>
        <p>{{ c(
          "Les LUFS et true peaks sont des estimations internes ×4. Pour une livraison réglementée, vérifier le WAV avec un mesureur certifié et comparer à niveau perçu égal.",
          "LUFS and true peaks are internal ×4 estimates. For regulated delivery, verify the WAV with a certified meter and compare at matched perceived loudness.",
        ) }}</p>
      </aside>
    </section>

    <footer class="technical-footer">
      <p>{{ c("Code, mesures et limites restent auditables.", "Code, measurements, and limits remain auditable.") }}</p>
      <button type="button" @click="$emit('studio')">{{ c("Tester dans le studio", "Test in the studio") }} →</button>
    </footer>
  </main>
</template>
