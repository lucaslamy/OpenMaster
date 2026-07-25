<script setup lang="ts">
import { computed, ref } from "vue";

import type { Locale } from "../i18n";
import { translate } from "../i18n";
import { interpolateSeries } from "../presentation";

const props = defineProps<{
  locale: Locale;
  title: string;
  description: string;
  before: number[];
  after: number[];
}>();
const reveal = ref(50);
const t = (key: string, variables?: Record<string, string | number>) =>
  translate(props.locale, key, variables);
const points = (values: number[]) =>
  values
    .map((value, index) => `${(index / Math.max(1, values.length - 1)) * 100},${50 - value * 43}`)
    .join(" ");
const beforePoints = computed(() => points(props.before));
const afterPoints = computed(() => points(props.after));
const interpolatedPoints = computed(() =>
  points(interpolateSeries(props.before, props.after, reveal.value)),
);
</script>

<template>
  <article class="comparison-chart">
    <header>
      <div><h3>{{ title }}</h3><p>{{ description }}</p></div>
      <output>{{ t("original") }} {{ 100 - reveal }}% · {{ t("master") }} {{ reveal }}%</output>
    </header>
    <div class="compare-waveform compact">
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        :aria-label="t('comparisonAria', { name: title.toLowerCase() })"
      >
        <polyline class="wave-reference wave-before" :points="beforePoints" />
        <polyline class="wave-reference wave-after" :points="afterPoints" />
        <polyline
          class="wave-interpolated"
          :points="interpolatedPoints"
          :style="{ '--master-mix': `${reveal}%` }"
        />
      </svg>
      <div class="compare-divider" :style="{ left: `${reveal}%` }"><span>↔</span></div>
      <input
        v-model.number="reveal"
        type="range"
        min="0"
        max="100"
        :aria-label="t('revealMaster', { name: title.toLowerCase() })"
      />
      <span class="compare-label before-label">0% · {{ t("original") }}</span>
      <span class="compare-label after-label">{{ t("master") }} · 100%</span>
    </div>
  </article>
</template>
