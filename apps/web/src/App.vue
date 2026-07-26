<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from "vue";

import {
  AnalysisApiClient,
  type AnalysisJob,
  createIdempotencyKey,
  isTerminalStatus,
} from "./api/analysis";
import AudioWaveform from "./components/AudioWaveform.vue";
import AnalysisDashboard from "./components/AnalysisDashboard.vue";
import BeforeAfterPlayer from "./components/BeforeAfterPlayer.vue";
import GuidePage from "./components/GuidePage.vue";
import InfoTip from "./components/InfoTip.vue";
import type { Locale } from "./i18n";
import { translate, translateApiError, translateFinding } from "./i18n";
import {
  recommendationFindings,
  stageIndex,
} from "./presentation";

const intents = [
  { key: "Transparent", copy: "Transparent", target: -16, ceiling: -1.5, gain: 6, depth: 24, eq: [0, 0, 0], clip: 0, spectral: [0, 0, 0, 0] },
  { key: "Streaming", copy: "Streaming", target: -14, ceiling: -1, gain: 9, depth: 24, eq: [0, 0, 0], clip: 1, spectral: [1.5, 1.5, 1.5, 0.1] },
  { key: "Podcast", copy: "Podcast", target: -16, ceiling: -1, gain: 6, depth: 16, eq: [-0.5, 1, 0.5], clip: 1, spectral: [2, 1, 4, 0.1] },
  { key: "Rap", copy: "Rap", target: -10, ceiling: -0.8, gain: 9, depth: 24, eq: [1, 0.5, 0.5], clip: 4, spectral: [2, 3, 3, 0.2] },
  { key: "Club", copy: "Club", target: -9, ceiling: -0.3, gain: 12, depth: 24, eq: [1.5, -0.5, 1], clip: 6, spectral: [2, 4, 2, 0.25] },
  { key: "Loud", copy: "Loud", target: -10, ceiling: -0.5, gain: 12, depth: 24, eq: [0.5, 0, 0.5], clip: 5, spectral: [3, 3, 3, 0.25] },
  { key: "Dynamic", copy: "Dynamic", target: -18, ceiling: -2, gain: 5, depth: 24, eq: [0, 0, 0], clip: 0, spectral: [0, 0, 0, 0] },
];
const storedLocale = localStorage.getItem("openmaster-locale");
const locale = ref<Locale>(
  storedLocale === "fr" || (storedLocale === null && navigator.language.startsWith("fr"))
    ? "fr"
    : "en",
);
const t = (key: string, variables?: Record<string, string | number>) =>
  translate(locale.value, key, variables);
const intentName = (intent: (typeof intents)[number]) => t(`intent${intent.copy}`);
const intentNote = (intent: (typeof intents)[number]) => t(`intent${intent.copy}Note`);
const intentDescription = (intent: (typeof intents)[number]) =>
  t(`intent${intent.copy}Description`);
const pipelineStages = computed(() => [
  { key: "queued", label: t("upload") },
  { key: "running", label: t("analysis") },
  { key: "mastering", label: t("mastering") },
  { key: "succeeded", label: t("ready") },
]);
const page = ref<"studio" | "guide">("studio");
const activeIntent = ref("Streaming");
const activeIntentLabel = computed(() => {
  if (activeIntent.value === "Custom") return t("custom");
  const intent = intents.find((candidate) => candidate.key === activeIntent.value);
  return intent ? intentName(intent) : t("custom");
});
const extraHeadroom = ref(false);
const gentleCorrection = ref(false);
const highResolution = ref(true);
const selectedFile = ref<File | null>(null);
const sourceUrl = ref<string | null>(null);
const job = ref<AnalysisJob | null>(null);
const error = ref<string | null>(null);
const submitting = ref(false);
const targetLufs = ref(-14);
const bitDepth = ref(24);
const maximumGainAdjustmentDb = ref(12);
const ceilingDbfs = ref(-1);
const eqLowGainDb = ref(0);
const eqMidGainDb = ref(0);
const eqHighGainDb = ref(0);
const clipperDriveDb = ref(1);
const limiterLookaheadMs = ref(3);
const limiterReleaseMs = ref(80);
const highPassEnabled = ref(true);
const highPassCutoffHz = ref(25);
const dynamicEqReductionDb = ref(0);
const bassControlReductionDb = ref(0);
const deEsserReductionDb = ref(0);
const saturationAmount = ref(0);
const showTechnical = ref(false);
const passwordDialogOpen = ref(false);
const masteringPassword = ref("");
const passwordError = ref<string | null>(null);
const client = new AnalysisApiClient();
const canSubmit = computed(() => selectedFile.value !== null && !submitting.value);
const currentStage = computed(() => (job.value ? stageIndex(job.value.status) : -1));
const findings = computed(() =>
  recommendationFindings(job.value?.recommendation).map((finding) => ({
    ...finding,
    message: translateFinding(locale.value, finding.code, finding.message),
  })),
);
const fileSize = computed(() =>
  selectedFile.value ? `${(selectedFile.value.size / 1024 / 1024).toFixed(1)} MB` : "",
);
let pollTimer: ReturnType<typeof setTimeout> | undefined;

function applyIntent(intent: (typeof intents)[number]): void {
  activeIntent.value = intent.key;
  targetLufs.value = intent.target;
  ceilingDbfs.value = intent.ceiling;
  maximumGainAdjustmentDb.value = intent.gain;
  bitDepth.value = intent.depth;
  [eqLowGainDb.value, eqMidGainDb.value, eqHighGainDb.value] = intent.eq;
  [
    dynamicEqReductionDb.value,
    bassControlReductionDb.value,
    deEsserReductionDb.value,
    saturationAmount.value,
  ] = intent.spectral;
  clipperDriveDb.value = intent.clip;
  extraHeadroom.value = intent.ceiling <= -1.5;
  gentleCorrection.value = intent.gain <= 6;
  highResolution.value = intent.depth >= 24;
}

function toggleHeadroom(): void {
  extraHeadroom.value = !extraHeadroom.value;
  ceilingDbfs.value = extraHeadroom.value ? -2 : -1;
  activeIntent.value = "Custom";
}

function toggleCorrection(): void {
  gentleCorrection.value = !gentleCorrection.value;
  maximumGainAdjustmentDb.value = gentleCorrection.value ? 6 : 12;
  activeIntent.value = "Custom";
}

function toggleResolution(): void {
  highResolution.value = !highResolution.value;
  bitDepth.value = highResolution.value ? 24 : 16;
  activeIntent.value = "Custom";
}

function selectFile(event: Event): void {
  const target = event.target as HTMLInputElement;
  setFile(target.files?.[0] ?? null);
}

function dropFile(event: DragEvent): void {
  setFile(event.dataTransfer?.files[0] ?? null);
}

function setFile(file: File | null): void {
  if (sourceUrl.value) URL.revokeObjectURL(sourceUrl.value);
  selectedFile.value = file;
  sourceUrl.value = file ? URL.createObjectURL(file) : null;
  job.value = null;
  error.value = null;
}

function requestMaster(): void {
  if (!canSubmit.value) return;
  masteringPassword.value = "";
  passwordError.value = null;
  passwordDialogOpen.value = true;
}

function closePasswordDialog(): void {
  passwordDialogOpen.value = false;
  masteringPassword.value = "";
  passwordError.value = null;
}

async function confirmMaster(): Promise<void> {
  if (!masteringPassword.value) {
    passwordError.value = t("passwordRequired");
    return;
  }
  const password = masteringPassword.value;
  closePasswordDialog();
  await submit(password);
}

async function submit(password: string): Promise<void> {
  if (!selectedFile.value) return;
  submitting.value = true;
  error.value = null;
  job.value = null;
  try {
    job.value = await client.submit(
      selectedFile.value,
      createIdempotencyKey(),
      targetLufs.value,
      bitDepth.value,
      maximumGainAdjustmentDb.value,
      ceilingDbfs.value,
      password,
      eqLowGainDb.value,
      eqMidGainDb.value,
      eqHighGainDb.value,
      clipperDriveDb.value,
      limiterLookaheadMs.value,
      limiterReleaseMs.value,
      highPassEnabled.value,
      highPassCutoffHz.value,
      dynamicEqReductionDb.value,
      bassControlReductionDb.value,
      deEsserReductionDb.value,
      saturationAmount.value,
    );
    schedulePoll();
  } catch (reason) {
    error.value =
      reason instanceof Error
        ? translateApiError(locale.value, reason.message)
        : t("requestFailed");
  } finally {
    submitting.value = false;
  }
}

function schedulePoll(): void {
  if (!job.value || isTerminalStatus(job.value.status)) return;
  pollTimer = setTimeout(async () => {
    if (!job.value) return;
    try {
      job.value = await client.get(job.value.id);
      schedulePoll();
    } catch (reason) {
      error.value =
        reason instanceof Error
          ? translateApiError(locale.value, reason.message)
          : t("statusFailed");
    }
  }, 1_000);
}

onBeforeUnmount(() => {
  if (pollTimer) clearTimeout(pollTimer);
  if (sourceUrl.value) URL.revokeObjectURL(sourceUrl.value);
});
watch(
  locale,
  (value) => {
    localStorage.setItem("openmaster-locale", value);
    document.documentElement.lang = value;
  },
  { immediate: true },
);
</script>

<template>
  <div class="app-shell">
    <nav class="topbar">
      <button class="brand brand-button" type="button" :aria-label="`OpenMaster ${t('studio')}`" @click="page = 'studio'">
        <span class="brand-mark"><i></i><i></i><i></i><i></i></span>
        <span>OPEN<span>MASTER</span></span>
      </button>
      <span class="studio-status"><i></i> {{ t("engineOnline") }}</span>
      <div class="nav-links">
        <button type="button" :class="{ active: page === 'studio' }" @click="page = 'studio'">{{ t("studio") }}</button>
        <button type="button" :class="{ active: page === 'guide' }" @click="page = 'guide'">{{ t("guide") }}</button>
        <label class="language-selector">
          <span class="sr-only">Language</span>
          <select v-model="locale" aria-label="Language / Langue">
            <option value="en">EN</option>
            <option value="fr">FR</option>
          </select>
        </label>
        <a class="github-link" href="https://github.com/lucaslamy/OpenMaster">{{ t("sourceLink") }}</a>
      </div>
    </nav>

    <GuidePage v-if="page === 'guide'" :locale="locale" @back="page = 'studio'" />
    <main v-else>
      <header class="hero">
        <p class="eyebrow">{{ t("workspace") }}</p>
        <h1>{{ t("heroTitle") }}<br /><em>{{ t("heroEmphasis") }}</em></h1>
        <p class="hero-copy">{{ t("heroCopy") }}</p>
      </header>

      <form class="studio-grid" @submit.prevent="requestMaster">
        <section class="panel source-panel">
          <div class="panel-heading">
            <div><span class="step">01</span><h2>{{ t("source") }}</h2></div>
            <span v-if="selectedFile" class="format-pill">{{ selectedFile.name.split(".").pop()?.toUpperCase() }}</span>
          </div>

          <label class="dropzone" for="audio-file" @dragover.prevent @drop.prevent="dropFile">
            <input id="audio-file" type="file" accept="audio/*,.wav,.flac,.mp3,.m4a,.ogg,.opus,.aiff" @change="selectFile" />
            <template v-if="selectedFile">
              <span class="file-icon">♫</span>
              <strong>{{ selectedFile.name }}</strong>
              <small>{{ fileSize }} · {{ t("ready") }}</small>
              <span class="replace">{{ t("chooseAnother") }}</span>
            </template>
            <template v-else>
              <span class="upload-icon">↑</span>
              <strong>{{ t("dropMix") }}</strong>
              <small>WAV, FLAC, MP3, AIFF, M4A, OGG or Opus</small>
              <span class="replace">{{ t("browse") }}</span>
            </template>
          </label>
          <AudioWaveform :file="selectedFile" :locale="locale" />
          <audio v-if="sourceUrl" class="audio-player" :src="sourceUrl" controls />
        </section>

        <aside class="panel settings-panel">
          <div class="panel-heading">
            <div><span class="step">02</span><h2>{{ t("direction") }}</h2></div>
          </div>

          <fieldset>
            <legend>{{ t("masteringIntent") }} <InfoTip :text="t('intentTip')" /></legend>
            <div class="preset-grid">
              <button
                v-for="intent in intents"
                :key="intent.key"
                class="preset"
                :class="{ active: activeIntent === intent.key }"
                :title="intentDescription(intent)"
                type="button"
                @click="applyIntent(intent)"
              >
                <span><strong>{{ intentName(intent) }}</strong><small>{{ intentNote(intent) }}</small></span>
                <b>{{ intent.target }}<small> LUFS</small></b>
              </button>
            </div>
          </fieldset>

          <fieldset class="continuous-control">
            <div class="control-heading">
              <legend>{{ t("customTarget") }} <InfoTip :text="t('customTargetTip')" /></legend>
              <output>{{ targetLufs.toFixed(1) }} LUFS</output>
            </div>
            <input
              v-model.number="targetLufs"
              type="range"
              min="-24"
              max="-8"
              step="0.5"
              :aria-label="t('customTarget')"
              @input="activeIntent = 'Custom'"
            />
            <div class="range-labels"><span>{{ t("dynamic") }} −24</span><span>{{ t("loud") }} −8</span></div>
          </fieldset>

          <fieldset>
            <legend>{{ t("wavDepth") }} <InfoTip :text="t('wavDepthTip')" /></legend>
            <div class="segments">
              <button
                v-for="depth in [16, 24, 32]"
                :key="depth"
                type="button"
                :class="{ active: bitDepth === depth }"
                @click="bitDepth = depth; activeIntent = 'Custom'"
              >{{ depth }} bit</button>
            </div>
          </fieldset>

          <fieldset class="continuous-control">
            <div class="control-heading">
              <legend>{{ t("limiterCeiling") }} <InfoTip :text="t('limiterTip')" /></legend>
              <output>{{ ceilingDbfs.toFixed(1) }} dBFS</output>
            </div>
            <input
              v-model.number="ceilingDbfs"
              type="range"
              min="-3"
              max="-0.1"
              step="0.1"
              :aria-label="t('limiterCeiling')"
              @input="activeIntent = 'Custom'"
            />
            <div class="range-labels"><span>{{ t("safer") }} −3 dB</span><span>{{ t("hot") }} −0.1 dB</span></div>
          </fieldset>

          <fieldset class="continuous-control">
            <div class="control-heading">
              <legend>{{ t("maxCorrection") }} <InfoTip :text="t('correctionTip')" /></legend>
              <output>±{{ maximumGainAdjustmentDb.toFixed(0) }} dB</output>
            </div>
            <input
              v-model.number="maximumGainAdjustmentDb"
              type="range"
              min="0"
              max="12"
              step="1"
              :aria-label="t('maxCorrection')"
              @input="activeIntent = 'Custom'"
            />
            <div class="range-labels"><span>{{ t("conservative") }}</span><span>{{ t("maximum") }}</span></div>
          </fieldset>

          <fieldset class="advanced-dsp">
            <legend>{{ t("tonalEqualizer") }} <InfoTip :text="t('tonalEqualizerTip')" /></legend>
            <div class="eq-curve" aria-hidden="true">
              <svg viewBox="0 0 300 70" preserveAspectRatio="none">
                <path class="eq-zero" d="M0 35 H300" />
                <polyline
                  :points="`0,${35 - eqLowGainDb * 4} 75,${35 - eqLowGainDb * 4} 150,${35 - eqMidGainDb * 4} 225,${35 - eqHighGainDb * 4} 300,${35 - eqHighGainDb * 4}`"
                />
              </svg>
            </div>
            <div class="mini-control">
              <label for="eq-low">{{ t("eqLow") }} <small>100 Hz</small></label>
              <output>{{ eqLowGainDb.toFixed(1) }} dB</output>
              <input id="eq-low" v-model.number="eqLowGainDb" type="range" min="-6" max="6" step="0.5" @input="activeIntent = 'Custom'" />
            </div>
            <div class="mini-control">
              <label for="eq-mid">{{ t("eqMid") }} <small>1 kHz</small></label>
              <output>{{ eqMidGainDb.toFixed(1) }} dB</output>
              <input id="eq-mid" v-model.number="eqMidGainDb" type="range" min="-6" max="6" step="0.5" @input="activeIntent = 'Custom'" />
            </div>
            <div class="mini-control">
              <label for="eq-high">{{ t("eqHigh") }} <small>10 kHz</small></label>
              <output>{{ eqHighGainDb.toFixed(1) }} dB</output>
              <input id="eq-high" v-model.number="eqHighGainDb" type="range" min="-6" max="6" step="0.5" @input="activeIntent = 'Custom'" />
            </div>
          </fieldset>

          <fieldset class="advanced-dsp">
            <legend>{{ t("spectralDynamics") }} <InfoTip :text="t('spectralDynamicsTip')" /></legend>
            <div class="mini-control switch-control">
              <label for="high-pass-enabled">{{ t("highPass") }} <InfoTip :text="t('highPassTip')" /></label>
              <input id="high-pass-enabled" v-model="highPassEnabled" type="checkbox" @change="activeIntent = 'Custom'" />
            </div>
            <div class="mini-control">
              <label for="high-pass-cutoff">{{ t("highPassCutoff") }}</label>
              <output>{{ highPassCutoffHz.toFixed(0) }} Hz</output>
              <input id="high-pass-cutoff" v-model.number="highPassCutoffHz" type="range" min="15" max="80" step="1" :disabled="!highPassEnabled" @input="activeIntent = 'Custom'" />
            </div>
            <div class="mini-control">
              <label for="dynamic-eq">{{ t("dynamicEq") }} <InfoTip :text="t('dynamicEqTip')" /></label>
              <output>{{ dynamicEqReductionDb.toFixed(1) }} dB</output>
              <input id="dynamic-eq" v-model.number="dynamicEqReductionDb" type="range" min="0" max="12" step="0.5" @input="activeIntent = 'Custom'" />
            </div>
            <div class="mini-control">
              <label for="bass-control">{{ t("bassControl") }} <InfoTip :text="t('bassControlTip')" /></label>
              <output>{{ bassControlReductionDb.toFixed(1) }} dB</output>
              <input id="bass-control" v-model.number="bassControlReductionDb" type="range" min="0" max="12" step="0.5" @input="activeIntent = 'Custom'" />
            </div>
            <div class="mini-control">
              <label for="de-esser">{{ t("deEsser") }} <InfoTip :text="t('deEsserTip')" /></label>
              <output>{{ deEsserReductionDb.toFixed(1) }} dB</output>
              <input id="de-esser" v-model.number="deEsserReductionDb" type="range" min="0" max="12" step="0.5" @input="activeIntent = 'Custom'" />
            </div>
            <div class="mini-control">
              <label for="saturation">{{ t("saturation") }} <InfoTip :text="t('saturationTip')" /></label>
              <output>{{ Math.round(saturationAmount * 100) }}%</output>
              <input id="saturation" v-model.number="saturationAmount" type="range" min="0" max="1" step="0.05" @input="activeIntent = 'Custom'" />
            </div>
          </fieldset>

          <fieldset class="advanced-dsp">
            <legend>{{ t("transientControl") }} <InfoTip :text="t('transientControlTip')" /></legend>
            <div class="mini-control">
              <label for="clipper-drive">{{ t("clipperDrive") }} <InfoTip :text="t('clipperDriveTip')" /></label>
              <output>{{ clipperDriveDb.toFixed(1) }} dB</output>
              <input id="clipper-drive" v-model.number="clipperDriveDb" type="range" min="0" max="12" step="0.5" @input="activeIntent = 'Custom'" />
            </div>
            <div class="mini-control">
              <label for="limiter-lookahead">{{ t("limiterLookahead") }} <InfoTip :text="t('limiterLookaheadTip')" /></label>
              <output>{{ limiterLookaheadMs.toFixed(1) }} ms</output>
              <input id="limiter-lookahead" v-model.number="limiterLookaheadMs" type="range" min="0" max="10" step="0.5" @input="activeIntent = 'Custom'" />
            </div>
            <div class="mini-control">
              <label for="limiter-release">{{ t("limiterRelease") }} <InfoTip :text="t('limiterReleaseTip')" /></label>
              <output>{{ limiterReleaseMs.toFixed(0) }} ms</output>
              <input id="limiter-release" v-model.number="limiterReleaseMs" type="range" min="10" max="500" step="10" @input="activeIntent = 'Custom'" />
            </div>
          </fieldset>

          <fieldset>
            <legend>{{ t("safeguards") }} <InfoTip :text="t('safeguardsTip')" /></legend>
            <div class="safeguard-grid">
              <button type="button" :class="{ active: extraHeadroom }" @click="toggleHeadroom" :title="t('extraHeadroomTip')">
                <span>◇</span><strong>{{ t("extraHeadroom") }}</strong><small>{{ t("extraHeadroomSmall") }}</small>
              </button>
              <button type="button" :class="{ active: gentleCorrection }" @click="toggleCorrection" :title="t('gentleCorrectionTip')">
                <span>↕</span><strong>{{ t("gentleCorrection") }}</strong><small>{{ t("gentleCorrectionSmall") }}</small>
              </button>
              <button type="button" :class="{ active: highResolution }" @click="toggleResolution" :title="t('highResolutionTip')">
                <span>✦</span><strong>{{ t("highResolution") }}</strong><small>{{ t("highResolutionSmall") }}</small>
              </button>
            </div>
          </fieldset>

          <div class="master-summary">
            <span>{{ t("activeProfile") }}</span>
            <strong>{{ activeIntentLabel }}</strong>
            <small>{{ t("outputSummary", { lufs: targetLufs.toFixed(1), ceiling: ceilingDbfs.toFixed(1), depth: bitDepth }) }}</small>
          </div>
          <button class="master-button" type="submit" :disabled="!canSubmit">
            <span>{{ submitting ? t("uploadSource") : t("createMaster") }}</span>
            <b>→</b>
          </button>
        </aside>
      </form>

      <p v-if="error" class="alert error" role="alert"><span>!</span>{{ error }}</p>

      <section v-if="job" class="results" aria-live="polite">
        <div class="pipeline panel">
          <div class="panel-heading">
            <div><span class="step">03</span><h2>{{ t("processing") }}</h2></div>
            <span class="job-id">{{ job.id.slice(0, 8) }}</span>
          </div>
          <ol>
            <li
              v-for="(stage, index) in pipelineStages"
              :key="stage.key"
              :class="{ done: currentStage > index, active: currentStage === index, failed: job.status === 'failed' && index === Math.max(currentStage, 0) }"
            >
              <span>{{ currentStage > index ? "✓" : index + 1 }}</span>
              <strong>{{ stage.label }}</strong>
            </li>
          </ol>
          <div v-if="!isTerminalStatus(job.status)" class="progress-line"><i></i></div>
        </div>

        <AnalysisDashboard
          v-if="job.result"
          :result="job.result"
          :target-lufs="targetLufs"
          :ceiling-dbfs="ceilingDbfs"
          :maximum-gain-adjustment-db="maximumGainAdjustmentDb"
          :bit-depth="bitDepth"
          :locale="locale"
        />

        <BeforeAfterPlayer
          v-if="sourceUrl && job.preview_url && job.source_waveform && job.master_waveform"
          :before-url="sourceUrl"
          :after-url="job.preview_url"
          :locale="locale"
          :before-waveform="job.source_waveform"
          :after-waveform="job.master_waveform"
          :before-spectrum="job.source_spectrum"
          :after-spectrum="job.master_spectrum"
          :before-level-timeline="job.source_level_timeline"
          :after-level-timeline="job.master_level_timeline"
        />

        <div v-if="findings.length" class="panel assistant-panel">
          <div class="assistant-intro">
            <span class="assistant-orb">✦</span>
            <div><p class="eyebrow">{{ t("assistant") }}</p><h2>{{ t("heard") }}</h2></div>
          </div>
          <ul>
            <li v-for="finding in findings" :key="finding.code">
              <span>↳</span>{{ finding.message }}
            </li>
          </ul>
        </div>

        <div v-if="job.download_url" class="delivery panel">
          <div>
            <p class="eyebrow">{{ t("masterReady") }}</p>
            <h2>{{ t("finalWaiting") }}</h2>
            <p>{{ t("privateDownload", { depth: bitDepth }) }}</p>
          </div>
          <a class="download" :href="job.download_url">{{ t("download") }} <span>↓</span></a>
        </div>

        <p v-if="job.error_message" class="alert error"><span>!</span>{{ job.error_message }}</p>

        <button v-if="job.result" class="technical-toggle" type="button" @click="showTechnical = !showTechnical">
          {{ showTechnical ? t("hide") : t("show") }} {{ t("technicalJson") }}
        </button>
        <div v-if="showTechnical" class="technical-grid">
          <pre>{{ JSON.stringify(job.result, null, 2) }}</pre>
          <pre v-if="job.recommendation">{{ JSON.stringify(job.recommendation, null, 2) }}</pre>
          <pre v-if="job.mastering_result">{{ JSON.stringify(job.mastering_result, null, 2) }}</pre>
        </div>
      </section>
    </main>

    <div
      v-if="passwordDialogOpen"
      class="modal-backdrop"
      role="presentation"
      @click.self="closePasswordDialog"
      @keydown.esc="closePasswordDialog"
    >
      <form class="password-dialog" role="dialog" aria-modal="true" :aria-labelledby="'password-title'" @submit.prevent="confirmMaster">
        <button class="modal-close" type="button" :aria-label="t('cancel')" @click="closePasswordDialog">×</button>
        <span class="lock-orb">⌁</span>
        <p class="eyebrow">{{ t("safeguards") }}</p>
        <h2 id="password-title">{{ t("unlockTitle") }}</h2>
        <p>{{ t("unlockCopy") }}</p>
        <label>
          <span>{{ t("password") }}</span>
          <input
            v-model="masteringPassword"
            type="password"
            autocomplete="current-password"
            :placeholder="t('passwordPlaceholder')"
            autofocus
          />
        </label>
        <p v-if="passwordError" class="modal-error" role="alert">{{ passwordError }}</p>
        <div class="modal-actions">
          <button type="button" @click="closePasswordDialog">{{ t("cancel") }}</button>
          <button type="submit">{{ t("authorize") }} <span>→</span></button>
        </div>
      </form>
    </div>

    <footer><span>OPENMASTER · 2026</span><span>{{ t("footer") }}</span></footer>
  </div>
</template>
