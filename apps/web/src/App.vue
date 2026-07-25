<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from "vue";

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
import {
  pipelineStages,
  recommendationFindings,
  stageIndex,
} from "./presentation";

const intents = [
  { name: "Transparent", note: "Preserve contrast", target: -16, ceiling: -1.5, gain: 6, depth: 24, description: "Gentle gain bounds and extra peak headroom preserve the source balance." },
  { name: "Streaming", note: "Balanced delivery", target: -14, ceiling: -1, gain: 9, depth: 24, description: "A neutral starting point for normalized music streaming playback." },
  { name: "Podcast", note: "Clear & controlled", target: -16, ceiling: -1, gain: 6, depth: 16, description: "Moderate loudness and conservative gain for spoken-word delivery." },
  { name: "Club", note: "Dense & forward", target: -9, ceiling: -0.3, gain: 12, depth: 24, description: "A loud target and high ceiling for dense playback systems; expect more limiting." },
  { name: "Loud", note: "Modern impact", target: -10, ceiling: -0.5, gain: 12, depth: 24, description: "Strong loudness with a small peak margin for modern high-impact masters." },
  { name: "Dynamic", note: "Maximum space", target: -18, ceiling: -2, gain: 5, depth: 24, description: "Lower loudness, wider headroom and restrained correction for dynamic material." },
];
const page = ref<"studio" | "guide">("studio");
const activeIntent = ref("Streaming");
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
const showTechnical = ref(false);
const client = new AnalysisApiClient();
const canSubmit = computed(() => selectedFile.value !== null && !submitting.value);
const currentStage = computed(() => (job.value ? stageIndex(job.value.status) : -1));
const findings = computed(() => recommendationFindings(job.value?.recommendation));
const fileSize = computed(() =>
  selectedFile.value ? `${(selectedFile.value.size / 1024 / 1024).toFixed(1)} MB` : "",
);
let pollTimer: ReturnType<typeof setTimeout> | undefined;

function applyIntent(intent: (typeof intents)[number]): void {
  activeIntent.value = intent.name;
  targetLufs.value = intent.target;
  ceilingDbfs.value = intent.ceiling;
  maximumGainAdjustmentDb.value = intent.gain;
  bitDepth.value = intent.depth;
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

async function submit(): Promise<void> {
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
    );
    schedulePoll();
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : "Mastering request failed";
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
      error.value = reason instanceof Error ? reason.message : "Job status request failed";
    }
  }, 1_000);
}

onBeforeUnmount(() => {
  if (pollTimer) clearTimeout(pollTimer);
  if (sourceUrl.value) URL.revokeObjectURL(sourceUrl.value);
});
</script>

<template>
  <div class="app-shell">
    <nav class="topbar">
      <button class="brand brand-button" type="button" aria-label="OpenMaster studio" @click="page = 'studio'">
        <span class="brand-mark"><i></i><i></i><i></i><i></i></span>
        <span>OPEN<span>MASTER</span></span>
      </button>
      <span class="studio-status"><i></i> Engine online</span>
      <div class="nav-links">
        <button type="button" :class="{ active: page === 'studio' }" @click="page = 'studio'">Studio</button>
        <button type="button" :class="{ active: page === 'guide' }" @click="page = 'guide'">Guide</button>
        <a class="github-link" href="https://github.com/lucaslamy/OpenMaster">Source ↗</a>
      </div>
    </nav>

    <GuidePage v-if="page === 'guide'" @back="page = 'studio'" />
    <main v-else>
      <header class="hero">
        <p class="eyebrow">Professional mastering workspace</p>
        <h1>Make every detail<br /><em>feel intentional.</em></h1>
        <p class="hero-copy">
          Deterministic audio analysis and mastering, accelerated on demand and fully
          transparent from source to final WAV.
        </p>
      </header>

      <form class="studio-grid" @submit.prevent="submit">
        <section class="panel source-panel">
          <div class="panel-heading">
            <div><span class="step">01</span><h2>Source</h2></div>
            <span v-if="selectedFile" class="format-pill">{{ selectedFile.name.split(".").pop()?.toUpperCase() }}</span>
          </div>

          <label class="dropzone" for="audio-file" @dragover.prevent @drop.prevent="dropFile">
            <input id="audio-file" type="file" accept="audio/*,.wav,.flac,.mp3,.m4a,.ogg,.opus,.aiff" @change="selectFile" />
            <template v-if="selectedFile">
              <span class="file-icon">♫</span>
              <strong>{{ selectedFile.name }}</strong>
              <small>{{ fileSize }} · Ready for processing</small>
              <span class="replace">Choose another track</span>
            </template>
            <template v-else>
              <span class="upload-icon">↑</span>
              <strong>Drop your mix here</strong>
              <small>WAV, FLAC, MP3, AIFF, M4A, OGG or Opus</small>
              <span class="replace">Browse files</span>
            </template>
          </label>
          <AudioWaveform :file="selectedFile" />
          <audio v-if="sourceUrl" class="audio-player" :src="sourceUrl" controls />
        </section>

        <aside class="panel settings-panel">
          <div class="panel-heading">
            <div><span class="step">02</span><h2>Direction</h2></div>
          </div>

          <fieldset>
            <legend>Mastering intent <InfoTip text="Applies a coherent starting point across loudness target, limiter ceiling, gain bounds and export depth. Every value remains editable." /></legend>
            <button
              v-for="intent in intents"
              :key="intent.name"
              class="preset"
              :class="{ active: activeIntent === intent.name }"
              :title="intent.description"
              type="button"
              @click="applyIntent(intent)"
            >
              <span><strong>{{ intent.name }}</strong><small>{{ intent.note }}</small></span>
              <b>{{ intent.target }}<small> LUFS</small></b>
            </button>
          </fieldset>

          <fieldset class="continuous-control">
            <div class="control-heading">
              <legend>Custom loudness target <InfoTip text="Changes the requested perceived programme loudness. Peak protection can reduce the effective gain when headroom is insufficient." /></legend>
              <output>{{ targetLufs.toFixed(1) }} LUFS</output>
            </div>
            <input
              v-model.number="targetLufs"
              type="range"
              min="-24"
              max="-8"
              step="0.5"
              aria-label="Custom loudness target"
              @input="activeIntent = 'Custom'"
            />
            <div class="range-labels"><span>Dynamic −24</span><span>Loud −8</span></div>
          </fieldset>

          <fieldset>
            <legend>WAV depth <InfoTip text="Sets the PCM resolution of the downloaded WAV. 24 bit is the normal production choice; 16 bit is common for final delivery." /></legend>
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
              <legend>Limiter ceiling <InfoTip text="Sets the highest linked sample peak allowed in the master. A lower ceiling leaves more playback and conversion headroom." /></legend>
              <output>{{ ceilingDbfs.toFixed(1) }} dBFS</output>
            </div>
            <input
              v-model.number="ceilingDbfs"
              type="range"
              min="-3"
              max="-0.1"
              step="0.1"
              aria-label="Limiter ceiling"
              @input="activeIntent = 'Custom'"
            />
            <div class="range-labels"><span>Safer −3 dB</span><span>Hot −0.1 dB</span></div>
          </fieldset>

          <fieldset class="continuous-control">
            <div class="control-heading">
              <legend>Maximum gain correction <InfoTip text="Limits how much automatic gain may raise or lower the track. Smaller values preserve more of the source level." /></legend>
              <output>±{{ maximumGainAdjustmentDb.toFixed(0) }} dB</output>
            </div>
            <input
              v-model.number="maximumGainAdjustmentDb"
              type="range"
              min="0"
              max="12"
              step="1"
              aria-label="Maximum gain correction"
              @input="activeIntent = 'Custom'"
            />
            <div class="range-labels"><span>Conservative</span><span>Maximum</span></div>
          </fieldset>

          <fieldset>
            <legend>Master safeguards <InfoTip text="Convenient policy switches that adjust existing deterministic controls. They never add hidden processing." /></legend>
            <div class="safeguard-grid">
              <button type="button" :class="{ active: extraHeadroom }" @click="toggleHeadroom" title="Sets the limiter ceiling to −2 dBFS for extra conversion and playback headroom.">
                <span>◇</span><strong>Extra headroom</strong><small>−2 dBFS ceiling</small>
              </button>
              <button type="button" :class="{ active: gentleCorrection }" @click="toggleCorrection" title="Limits automatic gain correction to ±6 dB to preserve more of the source balance.">
                <span>↕</span><strong>Gentle correction</strong><small>Maximum ±6 dB</small>
              </button>
              <button type="button" :class="{ active: highResolution }" @click="toggleResolution" title="Exports a 24-bit production WAV instead of a smaller 16-bit delivery file.">
                <span>✦</span><strong>High resolution</strong><small>24-bit PCM WAV</small>
              </button>
            </div>
          </fieldset>

          <button class="master-button" type="submit" :disabled="!canSubmit">
            <span>{{ submitting ? "Uploading source…" : "Create master" }}</span>
            <b>→</b>
          </button>
        </aside>
      </form>

      <p v-if="error" class="alert error" role="alert"><span>!</span>{{ error }}</p>

      <section v-if="job" class="results" aria-live="polite">
        <div class="pipeline panel">
          <div class="panel-heading">
            <div><span class="step">03</span><h2>Processing</h2></div>
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
        />

        <BeforeAfterPlayer
          v-if="sourceUrl && job.preview_url && job.source_waveform && job.master_waveform"
          :before-url="sourceUrl"
          :after-url="job.preview_url"
          :before-waveform="job.source_waveform"
          :after-waveform="job.master_waveform"
        />

        <div v-if="findings.length" class="panel assistant-panel">
          <div class="assistant-intro">
            <span class="assistant-orb">✦</span>
            <div><p class="eyebrow">Mastering assistant</p><h2>What the engine heard</h2></div>
          </div>
          <ul>
            <li v-for="finding in findings" :key="finding.code">
              <span>↳</span>{{ finding.message }}
            </li>
          </ul>
        </div>

        <div v-if="job.download_url" class="delivery panel">
          <div>
            <p class="eyebrow">Master ready</p>
            <h2>Your final WAV is waiting.</h2>
            <p>{{ bitDepth }}-bit export · private temporary download</p>
          </div>
          <a class="download" :href="job.download_url">Download master <span>↓</span></a>
        </div>

        <p v-if="job.error_message" class="alert error"><span>!</span>{{ job.error_message }}</p>

        <button v-if="job.result" class="technical-toggle" type="button" @click="showTechnical = !showTechnical">
          {{ showTechnical ? "Hide" : "Show" }} technical JSON
        </button>
        <div v-if="showTechnical" class="technical-grid">
          <pre>{{ JSON.stringify(job.result, null, 2) }}</pre>
          <pre v-if="job.recommendation">{{ JSON.stringify(job.recommendation, null, 2) }}</pre>
          <pre v-if="job.mastering_result">{{ JSON.stringify(job.mastering_result, null, 2) }}</pre>
        </div>
      </section>
    </main>

    <footer><span>OPENMASTER · 2026</span><span>Deterministic by design. Open by nature.</span></footer>
  </div>
</template>
