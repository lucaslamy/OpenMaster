<script setup lang="ts">
import { computed } from "vue";

import type { Locale } from "../i18n";
import { translate } from "../i18n";

interface AiChange {
  parameter: string;
  before: boolean | number;
  after: boolean | number;
}

const props = defineProps<{
  assistance: Record<string, unknown>;
  locale: Locale;
}>();

const t = (key: string) => translate(props.locale, key);
const changes = computed<AiChange[]>(() => {
  const value = props.assistance.changes;
  if (!Array.isArray(value)) return [];
  return value.filter(
    (change): change is AiChange =>
      typeof change === "object" &&
      change !== null &&
      typeof (change as AiChange).parameter === "string" &&
      ["boolean", "number"].includes(typeof (change as AiChange).before) &&
      ["boolean", "number"].includes(typeof (change as AiChange).after),
  );
});
const applied = computed(() => props.assistance.applied === true);
const model = computed(() =>
  typeof props.assistance.model === "string" ? props.assistance.model : "",
);
const rationale = computed(() =>
  typeof props.assistance.rationale === "string" ? props.assistance.rationale : "",
);

const parameterKeys: Record<string, string> = {
  target_lufs: "customTarget",
  maximum_gain_adjustment_db: "maxCorrection",
  ceiling_dbfs: "limiterCeiling",
  eq_low_gain_db: "eqLow",
  eq_mid_gain_db: "eqMid",
  eq_high_gain_db: "eqHigh",
  clipper_drive_db: "clipperDrive",
  limiter_lookahead_ms: "limiterLookahead",
  limiter_release_ms: "limiterRelease",
  high_pass_enabled: "highPass",
  high_pass_cutoff_hz: "highPassCutoff",
  dynamic_eq_reduction_db: "dynamicEq",
  bass_control_reduction_db: "bassControl",
  de_esser_reduction_db: "deEsser",
  saturation_amount: "saturation",
};

const ranges: Record<string, [number, number]> = {
  target_lufs: [-24, -8],
  maximum_gain_adjustment_db: [0, 12],
  ceiling_dbfs: [-6, -0.1],
  eq_low_gain_db: [-6, 6],
  eq_mid_gain_db: [-6, 6],
  eq_high_gain_db: [-6, 6],
  clipper_drive_db: [0, 12],
  limiter_lookahead_ms: [0, 10],
  limiter_release_ms: [10, 500],
  high_pass_cutoff_hz: [15, 80],
  dynamic_eq_reduction_db: [0, 12],
  bass_control_reduction_db: [0, 12],
  de_esser_reduction_db: [0, 12],
  saturation_amount: [0, 1],
};

function label(parameter: string): string {
  return t(parameterKeys[parameter] ?? parameter);
}

function format(parameter: string, value: boolean | number): string {
  if (typeof value === "boolean") return value ? t("enabled") : t("disabled");
  if (parameter === "target_lufs") return `${value.toFixed(1)} LUFS`;
  if (parameter.endsWith("_hz")) return `${value.toFixed(0)} Hz`;
  if (parameter.endsWith("_ms")) return `${value.toFixed(0)} ms`;
  if (parameter === "saturation_amount") return `${Math.round(value * 100)}%`;
  return `${value.toFixed(1)} dB`;
}

function position(parameter: string, value: boolean | number): number {
  if (typeof value === "boolean") return value ? 100 : 0;
  const range = ranges[parameter];
  if (!range) return 50;
  return Math.max(0, Math.min(100, ((value - range[0]) / (range[1] - range[0])) * 100));
}
</script>

<template>
  <section v-if="assistance.requested" class="panel ai-changes">
    <header>
      <div class="assistant-intro">
        <span class="assistant-orb">✦</span>
        <div>
          <p class="eyebrow">{{ t("aiChangesEyebrow") }}</p>
          <h2>{{ t("aiChangesTitle") }}</h2>
        </div>
      </div>
      <span :class="['ai-status', { applied }]">
        {{ applied ? t("aiApplied") : t("aiFallback") }}
      </span>
    </header>

    <template v-if="applied">
      <div v-if="rationale" class="ai-rationale-card">
        <span>{{ t("aiDecision") }}</span>
        <p class="ai-rationale">{{ rationale }}</p>
      </div>
      <div class="ai-meta">
        <div class="ai-model">
          <span>{{ t("aiModel") }}</span><strong>{{ model || "LamAI" }}</strong>
        </div>
        <span class="ai-mode">{{ t("aiIndependentMode") }}</span>
      </div>
      <div v-if="changes.length" class="ai-change-grid">
        <article v-for="change in changes" :key="change.parameter">
          <h3>{{ label(change.parameter) }}</h3>
          <div class="change-values">
            <span><small>{{ t("beforeAi") }}</small>{{ format(change.parameter, change.before) }}</span>
            <b>→</b>
            <span><small>{{ t("afterAi") }}</small>{{ format(change.parameter, change.after) }}</span>
          </div>
          <div class="change-track" aria-hidden="true">
            <i class="before-marker" :style="{ left: `${position(change.parameter, change.before)}%` }" />
            <i class="after-marker" :style="{ left: `${position(change.parameter, change.after)}%` }" />
          </div>
        </article>
      </div>
      <p v-else class="ai-no-change">{{ t("aiNoChange") }}</p>
      <p class="ai-audit-note">{{ t("aiAuditNote") }}</p>
    </template>
    <p v-else class="ai-no-change">{{ t("aiFallbackCopy") }}</p>
  </section>
</template>
