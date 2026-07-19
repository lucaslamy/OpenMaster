<script setup lang="ts">
import { computed, ref } from "vue";

import { AnalysisApiClient, type AnalysisJob, createIdempotencyKey } from "./api/analysis";

const selectedFile = ref<File | null>(null);
const job = ref<AnalysisJob | null>(null);
const error = ref<string | null>(null);
const submitting = ref(false);
const client = new AnalysisApiClient();
const canSubmit = computed(() => selectedFile.value !== null && !submitting.value);

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
    job.value = await client.submit(selectedFile.value, createIdempotencyKey());
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : "Analysis request failed";
  } finally {
    submitting.value = false;
  }
}
</script>

<template>
  <main>
    <header>
      <p class="eyebrow">OpenMaster v0.9</p>
      <h1>Analyse your master</h1>
      <p>Submit an audio file to the OpenMaster analysis service.</p>
    </header>

    <form @submit.prevent="submit">
      <label for="audio-file">Audio file</label>
      <input id="audio-file" type="file" accept="audio/*,.wav,.flac,.mp3,.m4a,.ogg,.opus,.aiff" @change="selectFile" />
      <button type="submit" :disabled="!canSubmit">{{ submitting ? "Submitting…" : "Analyse file" }}</button>
    </form>

    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <section v-if="job" aria-live="polite">
      <h2>Analysis job</h2>
      <dl>
        <dt>ID</dt><dd>{{ job.id }}</dd>
        <dt>Status</dt><dd>{{ job.status }}</dd>
      </dl>
    </section>
  </main>
</template>
