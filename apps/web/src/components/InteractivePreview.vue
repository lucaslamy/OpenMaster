<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import {
  masteringParameters,
  previewInputGainDb,
  type InteractiveSettings,
} from "../masteringParameters";

const props = defineProps<{ url: string; settings: InteractiveSettings; locale: "en" | "fr" }>();
const emit = defineEmits<{ reset: [] }>();
const audio = ref<HTMLAudioElement | null>(null);
const spectrum = ref<HTMLCanvasElement | null>(null);
const current = ref(0);
const duration = ref(0);
const mode = ref<"original" | "live">("live");
const loading = ref(true);
const playing = ref(false);
const refreshing = ref(false);
const error = ref("");
const mediaUrl = ref(props.url);
let context: AudioContext | null = null;
let source: MediaElementAudioSourceNode | null = null;
let filters: BiquadFilterNode[] = [];
let compressor: DynamicsCompressorNode | null = null;
let output: GainNode | null = null;
let analyser: AnalyserNode | null = null;
let masteringWorklet: AudioWorkletNode | null = null;
let graphPromise: Promise<void> | null = null;
let animationFrame = 0;
let refreshTimer: ReturnType<typeof setInterval> | undefined;
let resumeAt = 0;
let resumePlaying = false;
const baselineTargetLufs = Number(props.settings.targetLufs ?? -14);

const modified = computed(() => masteringParameters.filter((p) =>
  Number(props.settings[p.id] ?? p.defaultValue) !== p.defaultValue,
));
const formatTime = (seconds: number) => `${Math.floor(seconds / 60)}:${Math.floor(seconds % 60).toString().padStart(2, "0")}`;

async function buildGraph(): Promise<void> {
  if (!audio.value || context) return;
  context = new AudioContext();
  source = context.createMediaElementSource(audio.value);
  const low = context.createBiquadFilter(); low.type = "lowshelf"; low.frequency.value = 100;
  const mid = context.createBiquadFilter(); mid.type = "peaking"; mid.frequency.value = 1000; mid.Q.value = .7;
  const high = context.createBiquadFilter(); high.type = "highshelf"; high.frequency.value = 10000;
  const highPass = context.createBiquadFilter(); highPass.type = "highpass"; highPass.Q.value = .707;
  compressor = context.createDynamicsCompressor();
  output = context.createGain();
  analyser = context.createAnalyser();
  analyser.fftSize = 128;
  analyser.smoothingTimeConstant = .82;
  filters = [low, mid, high, highPass];
  source.connect(low).connect(mid).connect(high).connect(highPass).connect(compressor);
  try {
    await context.audioWorklet.addModule("/mastering-preview-worklet.js");
    masteringWorklet = new AudioWorkletNode(context, "mastering-preview");
    compressor.connect(masteringWorklet).connect(output);
  } catch {
    // Standard nodes remain a usable approximation on browsers without AudioWorklet.
    compressor.connect(output);
  }
  output.connect(analyser).connect(context.destination);
  applySettings();
  drawSpectrum();
}

function applySettings(): void {
  if (!context || !output || filters.length !== 4 || !compressor) return;
  const now = context.currentTime;
  const bypass = mode.value === "original";
  filters[0].gain.setTargetAtTime(bypass ? 0 : Number(props.settings.eqLowGainDb ?? 0), now, .02);
  filters[1].gain.setTargetAtTime(bypass ? 0 : Number(props.settings.eqMidGainDb ?? 0), now, .02);
  filters[2].gain.setTargetAtTime(bypass ? 0 : Number(props.settings.eqHighGainDb ?? 0), now, .02);
  filters[3].frequency.setTargetAtTime(bypass || props.settings.highPassEnabled === false ? 15 : Number(props.settings.highPassCutoffHz ?? 25), now, .02);
  const reduction = bypass ? 0 : Math.max(Number(props.settings.dynamicEqReductionDb ?? 0), Number(props.settings.bassControlReductionDb ?? 0), Number(props.settings.deEsserReductionDb ?? 0));
  compressor.threshold.setTargetAtTime(-8 - reduction, now, .02);
  compressor.ratio.setTargetAtTime(reduction === 0 ? 1 : 1 + reduction / 3, now, .02);
  if (masteringWorklet) {
    const workletParameters = masteringWorklet.parameters as unknown as {
      get(name: string): AudioParam | undefined;
    };
    const set = (name: string, value: number) =>
      workletParameters.get(name)?.setTargetAtTime(value, now, .02);
    const maximumGain = Number(props.settings.maximumGainAdjustmentDb ?? 12);
    set("inputGainDb", previewInputGainDb(
      Number(props.settings.targetLufs ?? baselineTargetLufs),
      baselineTargetLufs,
      maximumGain,
    ));
    set("saturation", Number(props.settings.saturationAmount ?? 0));
    set("clipperDriveDb", Number(props.settings.clipperDriveDb ?? 0));
    set("ceilingDbfs", Number(props.settings.ceilingDbfs ?? -1));
    set("lookaheadMs", Number(props.settings.limiterLookaheadMs ?? 3));
    set("releaseMs", Number(props.settings.limiterReleaseMs ?? 80));
    set("bitDepth", Number(props.settings.bitDepth ?? 24));
    set("bypass", bypass ? 1 : 0);
  }
  output.gain.setTargetAtTime(1, now, .02);
}

async function togglePlayback(): Promise<void> {
  if (!graphPromise) graphPromise = buildGraph();
  await graphPromise;
  if (context?.state === "suspended") await context.resume();
  if (!audio.value) return;
  if (audio.value.paused) await audio.value.play(); else audio.value.pause();
}

function drawSpectrum(): void {
  if (!analyser || !spectrum.value) return;
  const canvas = spectrum.value;
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  const width = Math.max(1, canvas.clientWidth);
  const height = Math.max(1, canvas.clientHeight);
  if (canvas.width !== width * ratio || canvas.height !== height * ratio) {
    canvas.width = width * ratio;
    canvas.height = height * ratio;
  }
  const drawing = canvas.getContext("2d");
  if (!drawing) return;
  const values = new Uint8Array(analyser.frequencyBinCount);
  analyser.getByteFrequencyData(values);
  drawing.clearRect(0, 0, canvas.width, canvas.height);
  const gap = 2 * ratio;
  const barWidth = canvas.width / values.length;
  values.forEach((value, index) => {
    const normalized = value / 255;
    const barHeight = Math.max(2 * ratio, normalized * canvas.height);
    const gradient = drawing.createLinearGradient(0, canvas.height, 0, 0);
    gradient.addColorStop(0, "rgba(110, 231, 193, .28)");
    gradient.addColorStop(1, "rgba(155, 140, 255, .95)");
    drawing.fillStyle = gradient;
    drawing.fillRect(index * barWidth, canvas.height - barHeight, Math.max(1, barWidth - gap), barHeight);
  });
  animationFrame = requestAnimationFrame(drawSpectrum);
}

function refreshedUrl(): string {
  const separator = props.url.includes("?") ? "&" : "?";
  return `${props.url}${separator}refresh=${Date.now()}`;
}

function refreshMedia(): void {
  if (!audio.value || refreshing.value) return;
  resumeAt = audio.value.currentTime || current.value;
  resumePlaying = !audio.value.paused;
  refreshing.value = true;
  error.value = "";
  mediaUrl.value = refreshedUrl();
}

async function mediaReady(): Promise<void> {
  if (!audio.value) return;
  duration.value = audio.value.duration || 0;
  if (refreshing.value) {
    audio.value.currentTime = Math.min(resumeAt, Math.max(0, duration.value - .1));
    if (resumePlaying) {
      try { await audio.value.play(); } catch { /* Browser may require another user gesture. */ }
    }
  }
  refreshing.value = false;
  loading.value = false;
  error.value = "";
}

function mediaFailed(): void {
  if (!refreshing.value) {
    refreshMedia();
    return;
  }
  refreshing.value = false;
  loading.value = false;
  error.value = props.locale === "fr"
    ? "La préécoute a été interrompue. Réessayez avec le bouton de reconnexion."
    : "Preview was interrupted. Retry with the reconnect button.";
}

watch(() => props.settings, applySettings, { deep: true });
watch(mode, applySettings);
watch(() => props.url, (value) => { mediaUrl.value = value; });
onMounted(() => {
  graphPromise = buildGraph();
  refreshTimer = setInterval(refreshMedia, 12 * 60 * 1000);
});
onBeforeUnmount(() => {
  if (refreshTimer) clearInterval(refreshTimer);
  cancelAnimationFrame(animationFrame);
  source?.disconnect();
  void context?.close();
});
</script>

<template>
  <section class="panel interactive-preview">
    <div class="panel-heading">
      <div><span class="preview-live-dot"></span><h2>{{ locale === "fr" ? "Pré-écoute" : "Preview" }}</h2></div>
      <span v-if="modified.length" class="modified-badge">{{ modified.length }} {{ locale === "fr" ? "modifié(s)" : "changed" }}</span>
    </div>
    <p class="preview-note">{{ locale === "fr" ? "Les réglages marqués ≈ sont une approximation navigateur. Le rendu final utilise le moteur complet." : "Settings marked ≈ are a browser approximation. The final render uses the complete engine." }}</p>
    <canvas ref="spectrum" class="live-spectrum" aria-hidden="true"></canvas>
    <audio
      ref="audio"
      :src="mediaUrl"
      crossorigin="anonymous"
      @loadedmetadata="mediaReady"
      @timeupdate="current = audio?.currentTime || 0"
      @play="playing = true"
      @pause="playing = false"
      @error="mediaFailed"
    />
    <div class="preview-transport">
      <button type="button" :disabled="loading || refreshing" @click="error ? refreshMedia() : togglePlayback()">{{ error ? "↻" : (playing ? "Ⅱ" : "▶") }}</button>
      <input aria-label="Preview position" type="range" min="0" :max="duration || 0" step=".01" :value="current" @input="audio && (audio.currentTime = Number(($event.target as HTMLInputElement).value))" />
      <time>{{ formatTime(current) }} / {{ formatTime(duration) }}</time>
    </div>
    <small v-if="refreshing" class="reconnecting">{{ locale === "fr" ? "Reconnexion à la source…" : "Refreshing source…" }}</small>
    <div class="ab-switch" role="group" :aria-label="locale === 'fr' ? 'Mode de préécoute' : 'Preview mode'">
      <button type="button" :class="{ active: mode === 'original' }" @click="mode = 'original'">{{ locale === "fr" ? "Original" : "Original" }}</button>
      <button type="button" :class="{ active: mode === 'live' }" @click="mode = 'live'">{{ locale === "fr" ? "Préécoute avec effets" : "Live effects preview" }}</button>
    </div>
    <p v-if="error" class="alert error" role="alert">{{ error }}</p>
  </section>
</template>
