<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from "vue";

import {
  AnalysisApiClient,
  type AnalysisJob,
  createIdempotencyKey,
  isTerminalStatus,
} from "./api/analysis";
import AudioWaveform from "./components/AudioWaveform.vue";
import {
  metric,
  meterPercent,
  peakHeadroom,
  pipelineStages,
  recommendationFindings,
  stageIndex,
  textMetric,
} from "./presentation";

const presets = [
  { value: -9, name: "Club", note: "Dense & loud" },
  { value: -14, name: "Streaming", note: "Balanced standard" },
  { value: -16, name: "Natural", note: "More dynamics" },
  { value: -18, name: "Wide", note: "Maximum breathing room" },
];
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
      <a class="brand" href="#" aria-label="OpenMaster home">
        <span class="brand-mark"><i></i><i></i><i></i><i></i></span>
        <span>OPEN<span>MASTER</span></span>
      </a>
      <span class="studio-status"><i></i> Engine online</span>
      <a class="github-link" href="https://github.com/lucaslamy/OpenMaster">Open source ↗</a>
    </nav>

    <main>
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
            <legend>Mastering profile</legend>
            <button
              v-for="preset in presets"
              :key="preset.value"
              class="preset"
              :class="{ active: targetLufs === preset.value }"
              type="button"
              @click="targetLufs = preset.value"
            >
              <span><strong>{{ preset.name }}</strong><small>{{ preset.note }}</small></span>
              <b>{{ preset.value }}<small> LUFS</small></b>
            </button>
          </fieldset>

          <fieldset class="continuous-control">
            <div class="control-heading">
              <legend>Custom loudness target</legend>
              <output>{{ targetLufs.toFixed(1) }} LUFS</output>
            </div>
            <input
              v-model.number="targetLufs"
              type="range"
              min="-24"
              max="-8"
              step="0.5"
              aria-label="Custom loudness target"
            />
            <div class="range-labels"><span>Dynamic −24</span><span>Loud −8</span></div>
          </fieldset>

          <fieldset>
            <legend>WAV depth</legend>
            <div class="segments">
              <button
                v-for="depth in [16, 24, 32]"
                :key="depth"
                type="button"
                :class="{ active: bitDepth === depth }"
                @click="bitDepth = depth"
              >{{ depth }} bit</button>
            </div>
          </fieldset>

          <fieldset class="continuous-control">
            <div class="control-heading">
              <legend>Limiter ceiling</legend>
              <output>{{ ceilingDbfs.toFixed(1) }} dBFS</output>
            </div>
            <input
              v-model.number="ceilingDbfs"
              type="range"
              min="-3"
              max="-0.1"
              step="0.1"
              aria-label="Limiter ceiling"
            />
            <div class="range-labels"><span>Safer −3 dB</span><span>Hot −0.1 dB</span></div>
          </fieldset>

          <fieldset class="continuous-control">
            <div class="control-heading">
              <legend>Maximum gain correction</legend>
              <output>±{{ maximumGainAdjustmentDb.toFixed(0) }} dB</output>
            </div>
            <input
              v-model.number="maximumGainAdjustmentDb"
              type="range"
              min="0"
              max="12"
              step="1"
              aria-label="Maximum gain correction"
            />
            <div class="range-labels"><span>Conservative</span><span>Maximum</span></div>
          </fieldset>

          <div class="safety-note">
            <span>◇</span>
            <p><strong>Deterministic safety</strong><br />Peak-aware gain and linked limiting stay auditable.</p>
          </div>

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

        <div v-if="job.result" class="metrics-grid">
          <article class="metric-card accent">
            <span>Integrated loudness</span>
            <strong>{{ metric(job.result, "lufs", " LUFS") }}</strong>
            <small>Target {{ targetLufs }} LUFS</small>
          </article>
          <article class="metric-card">
            <span>True peak</span>
            <strong>{{ metric(job.result, "true_peak_dbfs", " dB") }}</strong>
            <small>Estimated dBFS</small>
          </article>
          <article class="metric-card">
            <span>Dynamic range</span>
            <strong>{{ metric(job.result, "dynamic_range_db", " dB") }}</strong>
            <small>Crest {{ metric(job.result, "crest_factor_db", " dB") }}</small>
          </article>
          <article class="metric-card">
            <span>Tempo & key</span>
            <strong>{{ metric(job.result, "bpm", " BPM", 0) }}</strong>
            <small>{{ textMetric(job.result, "musical_key") }} · {{ metric(job.result, "duration_seconds", " sec", 0) }}</small>
          </article>
          <article class="metric-card">
            <span>Stereo image</span>
            <strong>{{ metric(job.result, "stereo_width", "", 2) }}</strong>
            <small>Phase {{ metric(job.result, "phase_correlation", "", 2) }}</small>
          </article>
          <article class="metric-card">
            <span>Spectral center</span>
            <strong>{{ metric(job.result, "spectral_centroid_hz", " Hz", 0) }}</strong>
            <small>{{ metric(job.result, "sample_rate_hz", " Hz", 0) }} source</small>
          </article>
          <article class="metric-card compact">
            <span>RMS energy</span>
            <strong>{{ metric(job.result, "rms_dbfs", " dB") }}</strong>
            <div class="meter"><i :style="{ width: `${meterPercent(job.result, 'rms_dbfs', -60, 0)}%` }"></i></div>
          </article>
          <article class="metric-card compact">
            <span>Sample peak</span>
            <strong>{{ metric(job.result, "peak_dbfs", " dB") }}</strong>
            <div class="meter hot"><i :style="{ width: `${meterPercent(job.result, 'peak_dbfs', -24, 0)}%` }"></i></div>
          </article>
          <article class="metric-card compact">
            <span>Phase correlation</span>
            <strong>{{ metric(job.result, "phase_correlation", "", 2) }}</strong>
            <div class="bipolar-meter"><i :style="{ left: `${meterPercent(job.result, 'phase_correlation', -1, 1)}%` }"></i></div>
          </article>
          <article class="metric-card compact">
            <span>Source format</span>
            <strong>{{ metric(job.result, "channels", " ch", 0) }}</strong>
            <small>{{ metric(job.result, "bit_depth", " bit", 0) }} · {{ metric(job.result, "sample_rate_hz", " Hz", 0) }}</small>
          </article>
          <article class="metric-card compact">
            <span>Peak headroom</span>
            <strong>{{ peakHeadroom(job.result, ceilingDbfs) }}</strong>
            <small>Ceiling configured at {{ ceilingDbfs.toFixed(1) }} dBFS</small>
          </article>
          <article class="metric-card compact">
            <span>Master policy</span>
            <strong>±{{ maximumGainAdjustmentDb }} dB</strong>
            <small>Maximum correction · {{ bitDepth }}-bit delivery</small>
          </article>
        </div>

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
