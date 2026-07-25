<script setup lang="ts">
import { computed, ref } from "vue";

const props = defineProps<{
  beforeUrl: string;
  afterUrl: string;
  beforeWaveform: number[];
  afterWaveform: number[];
}>();
const reveal = ref(50);
const mode = ref<"before" | "after">("before");
const before = ref<HTMLAudioElement | null>(null);
const after = ref<HTMLAudioElement | null>(null);
const points = (values: number[]) =>
  values.map((value, index) => `${(index / (values.length - 1)) * 100},${50 - value * 43}`).join(" ");
const beforePoints = computed(() => points(props.beforeWaveform));
const afterPoints = computed(() => points(props.afterWaveform));

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
      <div><span class="step">05</span><h2>Before / after</h2></div>
      <div class="ab-switch">
        <button type="button" :class="{ active: mode === 'before' }" @click="select('before')">A · Original</button>
        <button type="button" :class="{ active: mode === 'after' }" @click="select('after')">B · Master</button>
      </div>
    </div>
    <div class="compare-waveform">
      <svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-label="Original and mastered waveform comparison">
        <polyline class="wave-before" :points="beforePoints" />
        <g :style="{ clipPath: `inset(0 ${100 - reveal}% 0 0)` }">
          <polyline class="wave-after" :points="afterPoints" />
        </g>
      </svg>
      <div class="compare-divider" :style="{ left: `${reveal}%` }"><span>↔</span></div>
      <input v-model.number="reveal" type="range" min="0" max="100" aria-label="Reveal mastered waveform" />
      <span class="compare-label before-label">Original</span><span class="compare-label after-label">Master</span>
    </div>
    <audio ref="before" :class="{ visible: mode === 'before' }" :src="beforeUrl" controls preload="metadata" />
    <audio ref="after" :class="{ visible: mode === 'after' }" :src="afterUrl" controls preload="metadata" />
    <p>Switch A/B while playing to continue near the same timestamp. Match perceived volume before judging tonal differences.</p>
  </section>
</template>
