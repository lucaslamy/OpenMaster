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
const current = ref(0);
const duration = ref(0);
const mode = ref<"original" | "live">("live");
const loading = ref(true);
const error = ref("");
let context: AudioContext | null = null;
let source: MediaElementAudioSourceNode | null = null;
let filters: BiquadFilterNode[] = [];
let compressor: DynamicsCompressorNode | null = null;
let output: GainNode | null = null;
let masteringWorklet: AudioWorkletNode | null = null;
let graphPromise: Promise<void> | null = null;
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
  filters = [low, mid, high, highPass];
  source.connect(low).connect(mid).connect(high).connect(highPass).connect(compressor);
  try {
    await context.audioWorklet.addModule("/mastering-preview-worklet.js");
    masteringWorklet = new AudioWorkletNode(context, "mastering-preview");
    compressor.connect(masteringWorklet).connect(output).connect(context.destination);
  } catch {
    // Standard nodes remain a usable approximation on browsers without AudioWorklet.
    compressor.connect(output).connect(context.destination);
  }
  applySettings();
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

watch(() => props.settings, applySettings, { deep: true });
watch(mode, applySettings);
onMounted(() => { graphPromise = buildGraph(); });
onBeforeUnmount(() => { source?.disconnect(); void context?.close(); });
</script>

<template>
  <section class="panel interactive-preview">
    <div class="panel-heading">
      <div><span class="step">04</span><h2>{{ locale === "fr" ? "Pré-écoute interactive" : "Interactive preview" }}</h2></div>
      <span v-if="modified.length" class="modified-badge">{{ modified.length }} {{ locale === "fr" ? "modifié(s)" : "changed" }}</span>
    </div>
    <p class="preview-note">{{ locale === "fr" ? "Les réglages marqués ≈ sont une approximation navigateur. Le rendu final utilise le moteur complet." : "Settings marked ≈ are a browser approximation. The final render uses the complete engine." }}</p>
    <audio ref="audio" :src="url" crossorigin="anonymous" @loadedmetadata="duration = audio?.duration || 0; loading = false" @timeupdate="current = audio?.currentTime || 0" @error="error = locale === 'fr' ? 'Impossible de charger ou décoder la pré-écoute.' : 'The preview could not be loaded or decoded.'" />
    <div class="preview-transport">
      <button type="button" :disabled="loading || !!error" @click="togglePlayback">{{ audio?.paused !== false ? "▶" : "Ⅱ" }}</button>
      <input aria-label="Preview position" type="range" min="0" :max="duration || 0" step=".01" :value="current" @input="audio && (audio.currentTime = Number(($event.target as HTMLInputElement).value))" />
      <time>{{ formatTime(current) }} / {{ formatTime(duration) }}</time>
    </div>
    <div class="ab-switch" role="group" :aria-label="locale === 'fr' ? 'Mode de préécoute' : 'Preview mode'">
      <button type="button" :class="{ active: mode === 'original' }" @click="mode = 'original'">{{ locale === "fr" ? "Original" : "Original" }}</button>
      <button type="button" :class="{ active: mode === 'live' }" @click="mode = 'live'">{{ locale === "fr" ? "Préécoute avec effets" : "Live effects preview" }}</button>
    </div>
    <p v-if="error" class="alert error" role="alert">{{ error }}</p>
  </section>
</template>
