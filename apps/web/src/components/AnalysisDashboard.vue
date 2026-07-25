<script setup lang="ts">
import { ref } from "vue";

import {
  frequencyPercent,
  metric,
  meterPercent,
  peakHeadroom,
  textMetric,
} from "../presentation";
import type { Locale } from "../i18n";
import { translate, translateMusicalKey } from "../i18n";
import InfoTip from "./InfoTip.vue";

const props = defineProps<{
  result: Record<string, unknown>;
  targetLufs: number;
  ceilingDbfs: number;
  maximumGainAdjustmentDb: number;
  bitDepth: number;
  locale: Locale;
}>();
const views = [
  { key: "overview", label: "overview" },
  { key: "levels", label: "levels" },
  { key: "dynamics", label: "dynamics" },
  { key: "stereo", label: "stereo" },
  { key: "spectrum", label: "spectrum" },
  { key: "source", label: "sourceView" },
] as const;
type View = (typeof views)[number]["key"];
const activeView = ref<View>("overview");
const t = (key: string, variables?: Record<string, string | number>) =>
  translate(props.locale, key, variables);
</script>

<template>
  <section class="analysis-dashboard panel">
    <div class="panel-heading analysis-heading">
      <div><span class="step">04</span><h2>{{ t("soundSpecs") }}</h2></div>
      <span class="analysis-state">{{ t("analysisComplete") }}</span>
    </div>

    <div class="view-tabs" role="tablist" :aria-label="t('analysisViews')">
      <button
        v-for="view in views"
        :key="view.key"
        type="button"
        role="tab"
        :aria-selected="activeView === view.key"
        :class="{ active: activeView === view.key }"
        @click="activeView = view.key"
      >{{ t(view.label) }}</button>
    </div>

    <div v-if="activeView === 'overview'" class="analysis-view overview-view">
      <article class="hero-metric">
        <span>{{ t("integratedLoudness") }} <InfoTip :text="t('integratedTip')" /></span>
        <strong>{{ metric(result, "lufs", " LUFS") }}</strong>
        <div class="target-comparison">
          <i :style="{ width: `${meterPercent(result, 'lufs', -36, -6)}%` }"></i>
          <b :style="{ left: `${Math.max(0, Math.min(100, ((targetLufs + 36) / 30) * 100))}%` }"></b>
        </div>
        <small>{{ t("sourceTarget", { target: targetLufs }) }}</small>
      </article>
      <div class="overview-quadrants">
        <article><span>{{ t("truePeak") }}</span><strong>{{ metric(result, "true_peak_dbfs", " dBTP") }}</strong></article>
        <article><span>{{ t("dynamics") }}</span><strong>{{ metric(result, "dynamic_range_db", " dB") }}</strong></article>
        <article><span>{{ t("stereoWidth") }}</span><strong>{{ metric(result, "stereo_width", "", 2) }}</strong></article>
        <article><span>{{ t("musicalIdentity") }}</span><strong>{{ translateMusicalKey(locale, textMetric(result, "musical_key")) }}</strong><small>{{ metric(result, "bpm", " BPM", 0) }}</small></article>
      </div>
    </div>

    <div v-else-if="activeView === 'levels'" class="analysis-view gauge-list">
      <article>
        <header><span>{{ t("integratedLoudness") }} <InfoTip :text="t('integratedTechnicalTip')" /></span><strong>{{ metric(result, "lufs", " LUFS") }}</strong></header>
        <div class="scale-meter"><i :style="{ width: `${meterPercent(result, 'lufs', -36, 0)}%` }"></i></div>
        <footer><span>−36</span><span>{{ t("target") }} {{ targetLufs }}</span><span>0</span></footer>
      </article>
      <article>
        <header><span>{{ t("rmsEnergy") }} <InfoTip :text="t('rmsTip')" /></span><strong>{{ metric(result, "rms_dbfs", " dBFS") }}</strong></header>
        <div class="scale-meter violet"><i :style="{ width: `${meterPercent(result, 'rms_dbfs', -60, 0)}%` }"></i></div>
        <footer><span>{{ t("quiet") }}</span><span>{{ t("averageEnergy") }}</span><span>{{ t("dense") }}</span></footer>
      </article>
      <article>
        <header><span>{{ t("sampleTruePeak") }} <InfoTip :text="t('sampleTruePeakTip')" /></span><strong>{{ metric(result, "peak_dbfs", " / ") }}{{ metric(result, "true_peak_dbfs", " dB") }}</strong></header>
        <div class="scale-meter hot"><i :style="{ width: `${meterPercent(result, 'true_peak_dbfs', -24, 0)}%` }"></i></div>
        <footer><span>−24</span><span>{{ t("headroom") }} {{ peakHeadroom(result, ceilingDbfs) }}</span><span>0</span></footer>
      </article>
    </div>

    <div v-else-if="activeView === 'dynamics'" class="analysis-view dynamics-view">
      <div class="dynamic-orbit">
        <div><strong>{{ metric(result, "dynamic_range_db", "", 1) }}</strong><span>{{ t("dbRange") }}</span></div>
      </div>
      <div class="dynamic-copy">
        <p class="eyebrow">{{ t("macroDynamics") }}</p>
        <h3>{{ t("crestFactor", { value: metric(result, "crest_factor_db", " dB") }) }}</h3>
        <p>{{ t("dynamicsCopy") }}</p>
        <dl>
          <dt>{{ t("maxCorrection") }}</dt><dd>±{{ maximumGainAdjustmentDb }} dB</dd>
          <dt>{{ t("peakHeadroom") }}</dt><dd>{{ peakHeadroom(result, ceilingDbfs) }}</dd>
          <dt>{{ t("limiterCeiling") }}</dt><dd>{{ ceilingDbfs.toFixed(1) }} dBFS</dd>
        </dl>
      </div>
    </div>

    <div v-else-if="activeView === 'stereo'" class="analysis-view stereo-view">
      <div class="stereo-scope">
        <span class="scope-ring ring-one"></span><span class="scope-ring ring-two"></span>
        <i :style="{ width: `${20 + meterPercent(result, 'stereo_width', 0, 2) * 0.7}%` }"></i>
        <b :style="{ transform: `rotate(${(meterPercent(result, 'phase_correlation', -1, 1) - 50) * 0.8}deg)` }"></b>
      </div>
      <div class="stereo-stats">
        <article><span>{{ t("widthRatio") }} <InfoTip :text="t('widthTip')" /></span><strong>{{ metric(result, "stereo_width", "", 2) }}</strong></article>
        <article><span>{{ t("phaseCorrelation") }} <InfoTip :text="t('phaseTip')" /></span><strong>{{ metric(result, "phase_correlation", "", 2) }}</strong></article>
        <div class="phase-axis"><i :style="{ left: `${meterPercent(result, 'phase_correlation', -1, 1)}%` }"></i><span>−1 {{ t("risk") }}</span><span>0 {{ t("wide") }}</span><span>+1 {{ t("mono") }}</span></div>
      </div>
    </div>

    <div v-else-if="activeView === 'spectrum'" class="analysis-view spectrum-view">
      <div class="frequency-axis">
        <div class="frequency-glow" :style="{ left: `${frequencyPercent(result)}%` }"></div>
        <i :style="{ left: `${frequencyPercent(result)}%` }"></i>
        <span style="left: 0%">20 Hz</span><span style="left: 30%">100</span>
        <span style="left: 56%">1k</span><span style="left: 82%">10k</span><span style="left: 100%">20k</span>
      </div>
      <div class="spectrum-copy">
        <p class="eyebrow">{{ t("spectralCentroid") }}</p>
        <h3>{{ metric(result, "spectral_centroid_hz", " Hz", 0) }}</h3>
        <p>{{ t("centroidCopy") }}</p>
      </div>
    </div>

    <div v-else class="analysis-view source-view">
      <dl>
        <div><dt>{{ t("duration") }}</dt><dd>{{ metric(result, "duration_seconds", ` ${t("seconds")}`, 2) }}</dd></div>
        <div><dt>{{ t("sampleRate") }}</dt><dd>{{ metric(result, "sample_rate_hz", " Hz", 0) }}</dd></div>
        <div><dt>{{ t("sourceDepth") }}</dt><dd>{{ metric(result, "bit_depth", " bit", 0) }}</dd></div>
        <div><dt>{{ t("channels") }}</dt><dd>{{ metric(result, "channels", "", 0) }}</dd></div>
        <div><dt>{{ t("exportDepth") }}</dt><dd>{{ bitDepth }} bit PCM WAV</dd></div>
        <div><dt>{{ t("tempo") }}</dt><dd>{{ metric(result, "bpm", " BPM", 2) }}</dd></div>
        <div><dt>{{ t("keyEstimate") }}</dt><dd>{{ translateMusicalKey(locale, textMetric(result, "musical_key")) }}</dd></div>
        <div><dt>{{ t("analysisModel") }}</dt><dd>{{ t("deterministic") }} v0.7+</dd></div>
      </dl>
    </div>
  </section>
</template>
