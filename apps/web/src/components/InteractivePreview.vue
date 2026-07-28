<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import {
  masteringParameters,
  previewInputGainDb,
  type InteractiveSettings,
} from "../masteringParameters";

const props = defineProps<{
  url: string;
  settings: InteractiveSettings;
  locale: "en" | "fr";
  sourceLufs: number | null;
}>();
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
const graphError = ref("");
const workletAvailable = ref(true);
const mediaUrl = ref(props.url);
let context: AudioContext | null = null;
let source: MediaElementAudioSourceNode | null = null;
let filters: BiquadFilterNode[] = [];
let compressor: DynamicsCompressorNode | null = null;
let liveOutput: GainNode | null = null;
let originalOutput: GainNode | null = null;
let analyser: AnalyserNode | null = null;
let masteringWorklet: AudioWorkletNode | null = null;
let graphPromise: Promise<void> | null = null;
let animationFrame = 0;
let refreshTimer: ReturnType<typeof setInterval> | undefined;
let resumeAt = 0;
let resumePlaying = false;
let frequencyValues = new Uint8Array(0);

const modifiedCount = computed(() => {
  const parameterChanges = masteringParameters.filter((parameter) =>
    Number(props.settings[parameter.id] ?? parameter.defaultValue)
      !== parameter.defaultValue,
  ).length;
  return parameterChanges
    + (props.settings.highPassEnabled === false ? 1 : 0)
    + (props.settings.ai_assist_enabled === true ? 1 : 0);
});
const formatTime = (seconds: number) => `${Math.floor(seconds / 60)}:${Math.floor(seconds % 60).toString().padStart(2, "0")}`;

async function buildGraph(): Promise<void> {
  if (!audio.value || context) return;
  context = new AudioContext();
  source = context.createMediaElementSource(audio.value);
  const low = context.createBiquadFilter(); low.type = "peaking"; low.frequency.value = 100; low.Q.value = .7;
  const mid = context.createBiquadFilter(); mid.type = "peaking"; mid.frequency.value = 1000; mid.Q.value = 1;
  const high = context.createBiquadFilter(); high.type = "peaking"; high.frequency.value = 10000; high.Q.value = .7;
  const highPass = context.createBiquadFilter(); highPass.type = "highpass"; highPass.Q.value = .707;
  compressor = context.createDynamicsCompressor();
  liveOutput = context.createGain();
  originalOutput = context.createGain();
  liveOutput.gain.value = mode.value === "live" ? 1 : 0;
  originalOutput.gain.value = mode.value === "original" ? 1 : 0;
  analyser = context.createAnalyser();
  analyser.fftSize = 128;
  analyser.smoothingTimeConstant = .82;
  filters = [low, mid, high, highPass];
  source.connect(low).connect(mid).connect(high).connect(highPass).connect(compressor);
  try {
    await context.audioWorklet.addModule("/mastering-preview-worklet.js");
    masteringWorklet = new AudioWorkletNode(context, "mastering-preview");
    compressor.connect(masteringWorklet).connect(liveOutput);
  } catch {
    // Standard nodes remain a usable approximation on browsers without AudioWorklet.
    workletAvailable.value = false;
    compressor.connect(liveOutput);
  }
  source.connect(originalOutput);
  liveOutput.connect(analyser);
  originalOutput.connect(analyser);
  analyser.connect(context.destination);
  applySettings();
  drawSpectrum();
}

function applySettings(): void {
  if (
    !context
    || !liveOutput
    || !originalOutput
    || filters.length !== 4
    || !compressor
  ) return;
  const now = context.currentTime;
  const bypass = mode.value === "original";
  filters[0].gain.setTargetAtTime(bypass ? 0 : Number(props.settings.eqLowGainDb ?? 0), now, .02);
  filters[1].gain.setTargetAtTime(bypass ? 0 : Number(props.settings.eqMidGainDb ?? 0), now, .02);
  filters[2].gain.setTargetAtTime(bypass ? 0 : Number(props.settings.eqHighGainDb ?? 0), now, .02);
  filters[3].frequency.setTargetAtTime(bypass || props.settings.highPassEnabled === false ? 15 : Number(props.settings.highPassCutoffHz ?? 25), now, .02);
  // The final renderer applies three independent frequency-selective processors.
  // A single broadband browser compressor made bass hits pump the whole preview,
  // so it remains a clean pass-through instead of pretending to match that chain.
  compressor.threshold.setTargetAtTime(0, now, .02);
  compressor.ratio.setTargetAtTime(1, now, .02);
  if (masteringWorklet) {
    const workletParameters = masteringWorklet.parameters as unknown as {
      get(name: string): AudioParam | undefined;
    };
    const set = (name: string, value: number) =>
      workletParameters.get(name)?.setTargetAtTime(value, now, .02);
    const maximumGain = Number(props.settings.maximumGainAdjustmentDb ?? 12);
    const sourceLufs = Number.isFinite(props.sourceLufs)
      ? Number(props.sourceLufs)
      : Number(props.settings.targetLufs ?? -14);
    set("inputGainDb", previewInputGainDb(
      Number(props.settings.targetLufs ?? sourceLufs),
      sourceLufs,
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
  liveOutput.gain.setTargetAtTime(bypass ? 0 : 1, now, .01);
  originalOutput.gain.setTargetAtTime(bypass ? 1 : 0, now, .01);
}

async function togglePlayback(): Promise<void> {
  try {
    if (!graphPromise) graphPromise = buildGraph();
    await graphPromise;
    if (context?.state === "suspended") await context.resume();
    if (!audio.value) return;
    if (audio.value.paused) await audio.value.play(); else audio.value.pause();
    graphError.value = "";
  } catch {
    graphError.value = props.locale === "fr"
      ? "Le moteur de préécoute du navigateur n’a pas pu démarrer."
      : "The browser preview engine could not start.";
  }
}

function drawSpectrum(): void {
  animationFrame = 0;
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
  if (frequencyValues.length !== analyser.frequencyBinCount) {
    frequencyValues = new Uint8Array(analyser.frequencyBinCount);
  }
  analyser.getByteFrequencyData(frequencyValues);
  drawing.clearRect(0, 0, canvas.width, canvas.height);
  const gap = 2 * ratio;
  const barWidth = canvas.width / frequencyValues.length;
  const gradient = drawing.createLinearGradient(0, canvas.height, 0, 0);
  gradient.addColorStop(0, "rgba(110, 231, 193, .28)");
  gradient.addColorStop(1, "rgba(155, 140, 255, .95)");
  drawing.fillStyle = gradient;
  frequencyValues.forEach((value, index) => {
    const normalized = value / 255;
    const barHeight = Math.max(2 * ratio, normalized * canvas.height);
    drawing.fillRect(index * barWidth, canvas.height - barHeight, Math.max(1, barWidth - gap), barHeight);
  });
  if (playing.value) animationFrame = requestAnimationFrame(drawSpectrum);
}

function playbackStarted(): void {
  playing.value = true;
  if (!animationFrame) animationFrame = requestAnimationFrame(drawSpectrum);
}

function playbackStopped(): void {
  playing.value = false;
  cancelAnimationFrame(animationFrame);
  animationFrame = 0;
}

function refreshedUrl(): string {
  if (props.url.startsWith("blob:") || props.url.startsWith("data:")) {
    return props.url;
  }
  const separator = props.url.includes("?") ? "&" : "?";
  return `${props.url}${separator}refresh=${Date.now()}`;
}

function refreshMedia(): void {
  if (!audio.value || refreshing.value) return;
  resumeAt = audio.value.currentTime || current.value;
  resumePlaying = !audio.value.paused;
  refreshing.value = true;
  error.value = "";
  const nextUrl = refreshedUrl();
  if (nextUrl === mediaUrl.value) {
    audio.value.load();
  } else {
    mediaUrl.value = nextUrl;
  }
}

function scheduleMediaRefresh(url: string): void {
  if (refreshTimer) clearInterval(refreshTimer);
  refreshTimer = undefined;
  if (!url.startsWith("blob:") && !url.startsWith("data:")) {
    refreshTimer = setInterval(refreshMedia, 12 * 60 * 1000);
  }
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
watch(() => props.sourceLufs, applySettings);
watch(() => props.url, async (value) => {
  loading.value = true;
  refreshing.value = false;
  playbackStopped();
  current.value = 0;
  duration.value = 0;
  resumeAt = 0;
  resumePlaying = false;
  error.value = "";
  mediaUrl.value = value;
  scheduleMediaRefresh(value);
  await nextTick();
  audio.value?.load();
});
onMounted(() => {
  graphPromise = buildGraph();
  void graphPromise.catch(() => {
    graphError.value = props.locale === "fr"
      ? "Le moteur de préécoute du navigateur n’a pas pu démarrer."
      : "The browser preview engine could not start.";
  });
  scheduleMediaRefresh(props.url);
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
      <span v-if="modifiedCount" class="modified-badge">{{ modifiedCount }} {{ locale === "fr" ? "modifié(s)" : "changed" }}</span>
    </div>
    <p class="preview-note">{{ locale === "fr" ? "EQ, filtre, gain, saturation, clipper et limiteur sont audibles ici. EQ dynamique, contrôle du grave, de-esser et IA s’appliquent au rendu final." : "EQ, filtering, gain, saturation, clipping, and limiting are audible here. Dynamic EQ, bass control, de-essing, and AI apply to the final render." }}</p>
    <p v-if="!workletAvailable" class="reconnecting">{{ locale === "fr" ? "Mode dégradé : seuls l’EQ et le filtre sont audibles dans ce navigateur." : "Reduced mode: only EQ and filtering are audible in this browser." }}</p>
    <canvas ref="spectrum" class="live-spectrum" aria-hidden="true"></canvas>
    <audio
      ref="audio"
      :src="mediaUrl"
      crossorigin="anonymous"
      @loadedmetadata="mediaReady"
      @timeupdate="current = audio?.currentTime || 0"
      @play="playbackStarted"
      @pause="playbackStopped"
      @error="mediaFailed"
    />
    <div class="preview-transport">
      <button type="button" :aria-label="error ? (locale === 'fr' ? 'Reconnecter la préécoute' : 'Reconnect preview') : playing ? (locale === 'fr' ? 'Mettre en pause' : 'Pause') : (locale === 'fr' ? 'Lire' : 'Play')" :disabled="loading || refreshing" @click="error ? refreshMedia() : togglePlayback()">{{ error ? "↻" : (playing ? "Ⅱ" : "▶") }}</button>
      <input :aria-label="locale === 'fr' ? 'Position de préécoute' : 'Preview position'" type="range" min="0" :max="duration || 0" step=".01" :value="current" @input="audio && (audio.currentTime = Number(($event.target as HTMLInputElement).value))" />
      <time>{{ formatTime(current) }} / {{ formatTime(duration) }}</time>
    </div>
    <small v-if="refreshing" class="reconnecting">{{ locale === "fr" ? "Reconnexion à la source…" : "Refreshing source…" }}</small>
    <div class="ab-switch" role="group" :aria-label="locale === 'fr' ? 'Mode de préécoute' : 'Preview mode'">
      <button type="button" :aria-pressed="mode === 'original'" :class="{ active: mode === 'original' }" @click="mode = 'original'">{{ locale === "fr" ? "Original" : "Original" }}</button>
      <button type="button" :aria-pressed="mode === 'live'" :class="{ active: mode === 'live' }" @click="mode = 'live'">{{ locale === "fr" ? "Préécoute avec effets" : "Live effects preview" }}</button>
    </div>
    <p v-if="error" class="alert error" role="alert">{{ error }}</p>
    <p v-if="graphError" class="alert error" role="alert">{{ graphError }}</p>
  </section>
</template>
