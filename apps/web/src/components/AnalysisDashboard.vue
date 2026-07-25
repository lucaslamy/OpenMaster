<script setup lang="ts">
import { ref } from "vue";

import {
  frequencyPercent,
  metric,
  meterPercent,
  peakHeadroom,
  textMetric,
} from "../presentation";
import InfoTip from "./InfoTip.vue";

const props = defineProps<{
  result: Record<string, unknown>;
  targetLufs: number;
  ceilingDbfs: number;
  maximumGainAdjustmentDb: number;
  bitDepth: number;
}>();
const views = [
  { key: "overview", label: "Overview" },
  { key: "levels", label: "Levels" },
  { key: "dynamics", label: "Dynamics" },
  { key: "stereo", label: "Stereo" },
  { key: "spectrum", label: "Spectrum" },
  { key: "source", label: "Source" },
] as const;
type View = (typeof views)[number]["key"];
const activeView = ref<View>("overview");
</script>

<template>
  <section class="analysis-dashboard panel">
    <div class="panel-heading analysis-heading">
      <div><span class="step">04</span><h2>Sound specification</h2></div>
      <span class="analysis-state">Analysis complete</span>
    </div>

    <div class="view-tabs" role="tablist" aria-label="Analysis views">
      <button
        v-for="view in views"
        :key="view.key"
        type="button"
        role="tab"
        :aria-selected="activeView === view.key"
        :class="{ active: activeView === view.key }"
        @click="activeView = view.key"
      >{{ view.label }}</button>
    </div>

    <div v-if="activeView === 'overview'" class="analysis-view overview-view">
      <article class="hero-metric">
        <span>Integrated loudness <InfoTip text="Average perceived loudness over the complete track. Streaming services commonly normalize this value." /></span>
        <strong>{{ metric(result, "lufs", " LUFS") }}</strong>
        <div class="target-comparison">
          <i :style="{ width: `${meterPercent(result, 'lufs', -36, -6)}%` }"></i>
          <b :style="{ left: `${Math.max(0, Math.min(100, ((targetLufs + 36) / 30) * 100))}%` }"></b>
        </div>
        <small>Source level · target marker at {{ targetLufs }} LUFS</small>
      </article>
      <div class="overview-quadrants">
        <article><span>True peak</span><strong>{{ metric(result, "true_peak_dbfs", " dBTP") }}</strong></article>
        <article><span>Dynamics</span><strong>{{ metric(result, "dynamic_range_db", " dB") }}</strong></article>
        <article><span>Stereo width</span><strong>{{ metric(result, "stereo_width", "", 2) }}</strong></article>
        <article><span>Musical identity</span><strong>{{ textMetric(result, "musical_key") }}</strong><small>{{ metric(result, "bpm", " BPM", 0) }}</small></article>
      </div>
    </div>

    <div v-else-if="activeView === 'levels'" class="analysis-view gauge-list">
      <article>
        <header><span>Integrated LUFS <InfoTip text="Programme loudness after perceptual K-weighting and gating." /></span><strong>{{ metric(result, "lufs", " LUFS") }}</strong></header>
        <div class="scale-meter"><i :style="{ width: `${meterPercent(result, 'lufs', -36, 0)}%` }"></i></div>
        <footer><span>−36</span><span>Target {{ targetLufs }}</span><span>0</span></footer>
      </article>
      <article>
        <header><span>RMS energy <InfoTip text="Average electrical signal energy. Useful for comparing density independently from short peaks." /></span><strong>{{ metric(result, "rms_dbfs", " dBFS") }}</strong></header>
        <div class="scale-meter violet"><i :style="{ width: `${meterPercent(result, 'rms_dbfs', -60, 0)}%` }"></i></div>
        <footer><span>Quiet</span><span>Average energy</span><span>Dense</span></footer>
      </article>
      <article>
        <header><span>Sample / true peak <InfoTip text="Sample peak is the largest stored sample. True peak estimates inter-sample peaks that may appear during playback conversion." /></span><strong>{{ metric(result, "peak_dbfs", " / ") }}{{ metric(result, "true_peak_dbfs", " dB") }}</strong></header>
        <div class="scale-meter hot"><i :style="{ width: `${meterPercent(result, 'true_peak_dbfs', -24, 0)}%` }"></i></div>
        <footer><span>−24</span><span>Headroom {{ peakHeadroom(result, ceilingDbfs) }}</span><span>0</span></footer>
      </article>
    </div>

    <div v-else-if="activeView === 'dynamics'" class="analysis-view dynamics-view">
      <div class="dynamic-orbit">
        <div><strong>{{ metric(result, "dynamic_range_db", "", 1) }}</strong><span>dB range</span></div>
      </div>
      <div class="dynamic-copy">
        <p class="eyebrow">Macro dynamics</p>
        <h3>{{ metric(result, "crest_factor_db", " dB") }} crest factor</h3>
        <p>The gap between average energy and peaks indicates how much transient contrast remains in the mix.</p>
        <dl>
          <dt>Maximum correction</dt><dd>±{{ maximumGainAdjustmentDb }} dB</dd>
          <dt>Peak headroom</dt><dd>{{ peakHeadroom(result, ceilingDbfs) }}</dd>
          <dt>Limiter ceiling</dt><dd>{{ ceilingDbfs.toFixed(1) }} dBFS</dd>
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
        <article><span>Width ratio <InfoTip text="Side-to-mid energy ratio. Higher values indicate more side information; it is not a quality score." /></span><strong>{{ metric(result, "stereo_width", "", 2) }}</strong></article>
        <article><span>Phase correlation <InfoTip text="+1 is strongly correlated, 0 is decorrelated, and negative values can indicate mono-compatibility risks." /></span><strong>{{ metric(result, "phase_correlation", "", 2) }}</strong></article>
        <div class="phase-axis"><i :style="{ left: `${meterPercent(result, 'phase_correlation', -1, 1)}%` }"></i><span>−1 Risk</span><span>0 Wide</span><span>+1 Mono</span></div>
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
        <p class="eyebrow">Spectral centroid</p>
        <h3>{{ metric(result, "spectral_centroid_hz", " Hz", 0) }}</h3>
        <p>The centroid is the frequency “center of gravity”: a compact indication of overall brightness, not a full frequency response.</p>
      </div>
    </div>

    <div v-else class="analysis-view source-view">
      <dl>
        <div><dt>Duration</dt><dd>{{ metric(result, "duration_seconds", " seconds", 2) }}</dd></div>
        <div><dt>Sample rate</dt><dd>{{ metric(result, "sample_rate_hz", " Hz", 0) }}</dd></div>
        <div><dt>Source depth</dt><dd>{{ metric(result, "bit_depth", " bit", 0) }}</dd></div>
        <div><dt>Channels</dt><dd>{{ metric(result, "channels", "", 0) }}</dd></div>
        <div><dt>Export depth</dt><dd>{{ bitDepth }} bit PCM WAV</dd></div>
        <div><dt>Tempo</dt><dd>{{ metric(result, "bpm", " BPM", 2) }}</dd></div>
        <div><dt>Key estimate</dt><dd>{{ textMetric(result, "musical_key") }}</dd></div>
        <div><dt>Analysis model</dt><dd>Deterministic v0.7+</dd></div>
      </dl>
    </div>
  </section>
</template>
