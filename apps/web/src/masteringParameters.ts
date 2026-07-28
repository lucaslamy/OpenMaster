/** Canonical UI metadata for initial, interactive-preview, and final-render settings. */

export type PreviewCategory = "live" | "approximate" | "render";

export interface MasteringParameterDefinition {
  id: string;
  labelKey: string;
  min: number;
  max: number;
  defaultValue: number;
  step: number;
  unit: string;
  category: PreviewCategory;
  dsp?: "peak" | "highPass" | "compressor" | "output" | "worklet";
  backend: string;
}

export const masteringParameters: readonly MasteringParameterDefinition[] = [
  { id: "eqLowGainDb", labelKey: "eqLow", min: -6, max: 6, defaultValue: 0, step: .25, unit: "dB", category: "live", dsp: "peak", backend: "eq_low_gain_db" },
  { id: "eqMidGainDb", labelKey: "eqMid", min: -6, max: 6, defaultValue: 0, step: .25, unit: "dB", category: "live", dsp: "peak", backend: "eq_mid_gain_db" },
  { id: "eqHighGainDb", labelKey: "eqHigh", min: -6, max: 6, defaultValue: 0, step: .25, unit: "dB", category: "live", dsp: "peak", backend: "eq_high_gain_db" },
  { id: "highPassCutoffHz", labelKey: "highPassCutoff", min: 15, max: 80, defaultValue: 25, step: 1, unit: "Hz", category: "live", dsp: "highPass", backend: "high_pass_cutoff_hz" },
  { id: "dynamicEqReductionDb", labelKey: "dynamicEq", min: 0, max: 12, defaultValue: 0, step: .5, unit: "dB", category: "render", backend: "dynamic_eq_reduction_db" },
  { id: "bassControlReductionDb", labelKey: "bassControl", min: 0, max: 12, defaultValue: 0, step: .5, unit: "dB", category: "render", backend: "bass_control_reduction_db" },
  { id: "deEsserReductionDb", labelKey: "deEsser", min: 0, max: 12, defaultValue: 0, step: .5, unit: "dB", category: "render", backend: "de_esser_reduction_db" },
  { id: "targetLufs", labelKey: "customTarget", min: -24, max: -8, defaultValue: -14, step: .5, unit: "LUFS", category: "approximate", dsp: "worklet", backend: "target_lufs" },
  { id: "ceilingDbfs", labelKey: "limiterCeiling", min: -6, max: -.1, defaultValue: -1, step: .1, unit: "dBFS", category: "approximate", dsp: "output", backend: "ceiling_dbfs" },
  { id: "maximumGainAdjustmentDb", labelKey: "maxCorrection", min: 0, max: 12, defaultValue: 12, step: 1, unit: "dB", category: "approximate", dsp: "worklet", backend: "maximum_gain_adjustment_db" },
  { id: "clipperDriveDb", labelKey: "clipperDrive", min: 0, max: 12, defaultValue: 0, step: .5, unit: "dB", category: "approximate", dsp: "worklet", backend: "clipper_drive_db" },
  { id: "limiterLookaheadMs", labelKey: "limiterLookahead", min: 0, max: 10, defaultValue: 3, step: .5, unit: "ms", category: "approximate", dsp: "worklet", backend: "limiter_lookahead_ms" },
  { id: "limiterReleaseMs", labelKey: "limiterRelease", min: 10, max: 500, defaultValue: 80, step: 10, unit: "ms", category: "approximate", dsp: "worklet", backend: "limiter_release_ms" },
  { id: "saturationAmount", labelKey: "saturation", min: 0, max: 1, defaultValue: 0, step: .05, unit: "", category: "approximate", dsp: "worklet", backend: "saturation_amount" },
  { id: "bitDepth", labelKey: "wavDepth", min: 16, max: 32, defaultValue: 24, step: 8, unit: "bit", category: "approximate", dsp: "worklet", backend: "bit_depth" },
] as const;

export type InteractiveSettings = Record<string, number | boolean>;

export function backendSettings(values: InteractiveSettings): Record<string, number | boolean> {
  return Object.fromEntries(masteringParameters.map((parameter) => [
    parameter.backend,
    values[parameter.id] ?? parameter.defaultValue,
  ]));
}

export function previewInputGainDb(
  targetLufs: number,
  baselineTargetLufs: number,
  maximumGainAdjustmentDb: number,
): number {
  const requested = targetLufs - baselineTargetLufs;
  return Math.max(
    -maximumGainAdjustmentDb,
    Math.min(maximumGainAdjustmentDb, requested),
  );
}
