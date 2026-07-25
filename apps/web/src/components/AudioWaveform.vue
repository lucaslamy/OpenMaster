<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from "vue";

import type { Locale } from "../i18n";
import { translate } from "../i18n";

const props = defineProps<{ file: File | null; locale: Locale }>();
const t = (key: string) => translate(props.locale, key);
const canvas = ref<HTMLCanvasElement | null>(null);
const loading = ref(false);
const message = ref("");
let context: AudioContext | null = null;
let renderToken = 0;

async function render(file: File | null): Promise<void> {
  const token = ++renderToken;
  if (!file) {
    message.value = t("selectPreview");
    clearCanvas();
    return;
  }
  if (file.size > 128 * 1024 * 1024) {
    clearCanvas();
    message.value = t("previewSkipped");
    return;
  }
  loading.value = true;
  message.value = t("readingWaveform");
  try {
    context ??= new AudioContext();
    const audio = await context.decodeAudioData(await file.arrayBuffer());
    if (token !== renderToken) return;
    await nextTick();
    draw(audio);
    message.value = `${formatDuration(audio.duration)} · ${audio.sampleRate / 1000} kHz`;
  } catch {
    if (token !== renderToken) return;
    clearCanvas();
    message.value = t("previewUnavailable");
  } finally {
    if (token === renderToken) loading.value = false;
  }
}

function draw(audio: AudioBuffer): void {
  const element = canvas.value;
  if (!element) return;
  const scale = window.devicePixelRatio || 1;
  const width = element.clientWidth || 900;
  const height = element.clientHeight || 220;
  element.width = width * scale;
  element.height = height * scale;
  const drawing = element.getContext("2d");
  if (!drawing) return;
  drawing.scale(scale, scale);
  const gradient = drawing.createLinearGradient(0, 0, width, 0);
  gradient.addColorStop(0, "#6ee7c1");
  gradient.addColorStop(0.55, "#8b9cff");
  gradient.addColorStop(1, "#d887ff");
  drawing.fillStyle = gradient;
  const channels = Array.from({ length: audio.numberOfChannels }, (_, index) =>
    audio.getChannelData(index),
  );
  const samplesPerBar = Math.max(1, Math.floor(audio.length / width));
  const center = height / 2;
  const gap = 2;
  for (let x = 0; x < width; x += gap) {
    let peak = 0;
    const start = x * samplesPerBar;
    const end = Math.min(start + samplesPerBar, audio.length);
    for (const channel of channels) {
      for (let index = start; index < end; index += Math.max(1, Math.floor(samplesPerBar / 24))) {
        peak = Math.max(peak, Math.abs(channel[index] ?? 0));
      }
    }
    const barHeight = Math.max(2, peak * (height - 18));
    drawing.globalAlpha = 0.45 + peak * 0.55;
    drawing.roundRect(x, center - barHeight / 2, 1.5, barHeight, 2);
    drawing.fill();
  }
}

function clearCanvas(): void {
  const element = canvas.value;
  const drawing = element?.getContext("2d");
  if (element && drawing) drawing.clearRect(0, 0, element.width, element.height);
}

function formatDuration(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${Math.floor(seconds % 60).toString().padStart(2, "0")}`;
}

watch(() => props.file, render, { immediate: true });
watch(() => props.locale, () => render(props.file));
onBeforeUnmount(() => {
  renderToken++;
  void context?.close();
});
</script>

<template>
  <div class="waveform" :class="{ loading }">
    <canvas ref="canvas" :aria-label="t('selectPreview')"></canvas>
    <div class="waveform-axis"><span>0:00</span><span>{{ message }}</span><span>{{ t("end") }}</span></div>
  </div>
</template>
