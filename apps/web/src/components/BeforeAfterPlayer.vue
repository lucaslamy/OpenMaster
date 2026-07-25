<script setup lang="ts">
import { computed, ref } from "vue";

import type { Locale } from "../i18n";
import { translate } from "../i18n";
import { movingPeakDensity, transientActivity } from "../presentation";
import ComparisonChart from "./ComparisonChart.vue";

const props = defineProps<{
  locale: Locale;
  beforeUrl: string;
  afterUrl: string;
  beforeWaveform: number[];
  afterWaveform: number[];
}>();
const mode = ref<"before" | "after">("before");
const before = ref<HTMLAudioElement | null>(null);
const after = ref<HTMLAudioElement | null>(null);
const t = (key: string, variables?: Record<string, string | number>) =>
  translate(props.locale, key, variables);
const comparisons = computed(() => [
  {
    key: "peaks",
    title: t("peakEnvelope"),
    description: t("peakEnvelopeHelp"),
    before: props.beforeWaveform,
    after: props.afterWaveform,
  },
  {
    key: "density",
    title: t("peakDensity"),
    description: t("peakDensityHelp"),
    before: movingPeakDensity(props.beforeWaveform),
    after: movingPeakDensity(props.afterWaveform),
  },
  {
    key: "transients",
    title: t("transientActivity"),
    description: t("transientActivityHelp"),
    before: transientActivity(props.beforeWaveform),
    after: transientActivity(props.afterWaveform),
  },
]);

async function select(next: "before" | "after"): Promise<void> {
  const currentPlayer = mode.value === "before" ? before.value : after.value;
  const nextPlayer = next === "before" ? before.value : after.value;
  if (!nextPlayer) return;
  const wasPlaying = currentPlayer ? !currentPlayer.paused : false;
  if (currentPlayer) {
    nextPlayer.currentTime = currentPlayer.currentTime;
    currentPlayer.pause();
  }
  mode.value = next;
  if (wasPlaying) await nextPlayer.play();
}
</script>

<template>
  <section class="ab-player panel">
    <div class="panel-heading">
      <div><span class="step">05</span><h2>{{ t("beforeAfter") }}</h2></div>
      <div class="ab-switch">
        <button type="button" :class="{ active: mode === 'before' }" @click="select('before')">A · {{ t("original") }}</button>
        <button type="button" :class="{ active: mode === 'after' }" @click="select('after')">B · {{ t("master") }}</button>
      </div>
    </div>
    <div class="comparison-grid">
      <ComparisonChart
        v-for="comparison in comparisons"
        :key="comparison.key"
        :locale="locale"
        :title="comparison.title"
        :description="comparison.description"
        :before="comparison.before"
        :after="comparison.after"
      />
    </div>
    <audio ref="before" :class="{ visible: mode === 'before' }" :src="beforeUrl" controls preload="metadata" />
    <audio ref="after" :class="{ visible: mode === 'after' }" :src="afterUrl" controls preload="metadata" />
    <p>{{ t("abHelp") }}</p>
    <p class="graph-disclaimer">{{ t("graphDisclaimer") }}</p>
  </section>
</template>
