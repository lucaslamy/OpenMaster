import type { AnalysisJob } from "./api/analysis";

export const pipelineStages = [
  { key: "queued", label: "Upload" },
  { key: "running", label: "Analysis" },
  { key: "mastering", label: "Mastering" },
  { key: "succeeded", label: "Ready" },
] as const;

export function stageIndex(status: AnalysisJob["status"]): number {
  if (status === "failed") return -1;
  if (status === "retry_wait") return 1;
  return Math.max(0, pipelineStages.findIndex((stage) => stage.key === status));
}

export function metric(
  result: Record<string, unknown> | undefined,
  key: string,
  suffix = "",
  digits = 1,
): string {
  const value = result?.[key];
  return typeof value === "number" && Number.isFinite(value)
    ? `${value.toFixed(digits)}${suffix}`
    : "—";
}

export function textMetric(
  result: Record<string, unknown> | undefined,
  key: string,
): string {
  const value = result?.[key];
  return typeof value === "string" && value.length > 0 ? value : "—";
}

export function recommendationFindings(
  recommendation: Record<string, unknown> | undefined,
): Array<{ code: string; message: string }> {
  const findings = recommendation?.findings;
  if (!Array.isArray(findings)) return [];
  return findings.filter(
    (finding): finding is { code: string; message: string } =>
      typeof finding === "object" &&
      finding !== null &&
      typeof (finding as Record<string, unknown>).code === "string" &&
      typeof (finding as Record<string, unknown>).message === "string",
  );
}

export function meterPercent(
  result: Record<string, unknown> | undefined,
  key: string,
  minimum: number,
  maximum: number,
): number {
  const value = result?.[key];
  if (typeof value !== "number" || !Number.isFinite(value) || maximum <= minimum) return 0;
  return Math.round(Math.max(0, Math.min(1, (value - minimum) / (maximum - minimum))) * 100);
}

export function peakHeadroom(
  result: Record<string, unknown> | undefined,
  ceilingDbfs: number,
): string {
  const peak = result?.peak_dbfs;
  return typeof peak === "number" && Number.isFinite(peak)
    ? `${Math.max(0, ceilingDbfs - peak).toFixed(1)} dB`
    : "—";
}

export function frequencyPercent(result: Record<string, unknown> | undefined): number {
  const value = result?.spectral_centroid_hz;
  if (typeof value !== "number" || !Number.isFinite(value) || value <= 0) return 0;
  const minimum = Math.log10(20);
  const maximum = Math.log10(20_000);
  return Math.round(
    Math.max(0, Math.min(1, (Math.log10(value) - minimum) / (maximum - minimum))) * 100,
  );
}
