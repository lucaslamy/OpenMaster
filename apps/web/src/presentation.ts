import type { AnalysisJob } from "./api/analysis";

export interface JobStatusSnapshot {
  id: string;
  status: AnalysisJob["status"];
}

export function shouldScrollToComparison(
  previous: JobStatusSnapshot | null,
  current: JobStatusSnapshot | null,
): boolean {
  return (
    previous !== null
    && current !== null
    && previous.id === current.id
    && previous.status === "mastering"
    && current.status === "succeeded"
  );
}

export function stageIndex(status: AnalysisJob["status"]): number {
  if (status === "failed") return -1;
  if (status === "queued" || status === "running" || status === "retry_wait") return 1;
  if (status === "analyzed") return 2;
  if (status === "mastering") return 3;
  return 4;
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

export function movingPeakDensity(values: number[], radius = 4): number[] {
  // Return a bounded moving RMS view of an already compact peak envelope.
  if (radius < 1) return [...values];
  return values.map((_, index) => {
    const window = values.slice(Math.max(0, index - radius), index + radius + 1);
    const meanSquare =
      window.reduce((total, value) => total + Math.max(0, value) ** 2, 0) / window.length;
    return Math.min(1, Math.sqrt(meanSquare));
  });
}

export function transientActivity(values: number[]): number[] {
  // Highlight bounded point-to-point changes without inventing spectral data.
  if (values.length === 0) return [];
  return values.map((value, index) =>
    index === 0 ? 0 : Math.abs(value - (values[index - 1] ?? value)),
  );
}

export function interpolateSeries(before: number[], after: number[], percent: number): number[] {
  const ratio = Math.max(0, Math.min(100, percent)) / 100;
  const length = Math.min(before.length, after.length);
  return Array.from(
    { length },
    (_, index) => (before[index] ?? 0) * (1 - ratio) + (after[index] ?? 0) * ratio,
  );
}
