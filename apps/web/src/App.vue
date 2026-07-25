<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from "vue";

import {
  AnalysisApiClient,
  type AnalysisJob,
  createIdempotencyKey,
  isTerminalStatus,
} from "./api/analysis";

const selectedFile = ref<File | null>(null);
const job = ref<AnalysisJob | null>(null);
const error = ref<string | null>(null);
const submitting = ref(false);
const targetLufs = ref(-14);
const bitDepth = ref(24);
const client = new AnalysisApiClient();
const canSubmit = computed(() => selectedFile.value !== null && !submitting.value);
let pollTimer: ReturnType<typeof setTimeout> | undefined;

function selectFile(event: Event): void {
  const target = event.target as HTMLInputElement;
  selectedFile.value = target.files?.[0] ?? null;
  error.value = null;
}

async function submit(): Promise<void> {
  if (!selectedFile.value) return;
  submitting.value = true;
  error.value = null;
  try {
    job.value = await client.submit(
      selectedFile.value,
      createIdempotencyKey(),
      targetLufs.value,
      bitDepth.value,
    );
    schedulePoll();
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : "Analysis request failed";
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
});
</script>

<template>
  <main>
    <header>
      <p class="eyebrow">OpenMaster</p>
      <h1>Analyse and master your track</h1>
      <p>Upload once, review the analysis and recommendation, then download the mastered WAV.</p>
    </header>

    <form @submit.prevent="submit">
      <label for="audio-file">Audio file</label>
      <input id="audio-file" type="file" accept="audio/*,.wav,.flac,.mp3,.m4a,.ogg,.opus,.aiff" @change="selectFile" />
      <label for="target-lufs">Target loudness</label>
      <select id="target-lufs" v-model.number="targetLufs">
        <option :value="-9">-9 LUFS — loud</option>
        <option :value="-14">-14 LUFS — streaming</option>
        <option :value="-16">-16 LUFS — balanced</option>
        <option :value="-18">-18 LUFS — dynamic</option>
      </select>
      <label for="bit-depth">WAV export</label>
      <select id="bit-depth" v-model.number="bitDepth">
        <option :value="16">16 bit</option>
        <option :value="24">24 bit</option>
        <option :value="32">32 bit</option>
      </select>
      <button type="submit" :disabled="!canSubmit">
        {{ submitting ? "Uploading…" : "Analyse and master" }}
      </button>
    </form>

    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <section v-if="job" aria-live="polite">
      <h2>Analysis job</h2>
      <dl>
        <dt>ID</dt><dd>{{ job.id }}</dd>
        <dt>Status</dt><dd>{{ job.status }}</dd>
      </dl>
      <h3 v-if="job.result">Audio analysis</h3>
      <pre v-if="job.result">{{ JSON.stringify(job.result, null, 2) }}</pre>
      <h3 v-if="job.recommendation">Mastering assistant</h3>
      <pre v-if="job.recommendation">{{ JSON.stringify(job.recommendation, null, 2) }}</pre>
      <h3 v-if="job.mastering_result">Mastering result</h3>
      <pre v-if="job.mastering_result">{{ JSON.stringify(job.mastering_result, null, 2) }}</pre>
      <a v-if="job.download_url" class="download" :href="job.download_url">
        Download mastered WAV
      </a>
      <p v-if="job.error_message" class="error">{{ job.error_message }}</p>
    </section>
  </main>
</template>
