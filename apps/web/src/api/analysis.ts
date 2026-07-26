/** Typed HTTP boundary for OpenMaster analysis-job operations. */

export interface AnalysisJob {
  id: string;
  status: "queued" | "running" | "mastering" | "retry_wait" | "succeeded" | "failed";
  result?: Record<string, unknown>;
  recommendation?: Record<string, unknown>;
  mastering_result?: Record<string, unknown>;
  download_url?: string;
  preview_url?: string;
  initial_preview_url?: string;
  source_waveform?: number[];
  master_waveform?: number[];
  source_spectrum?: number[];
  master_spectrum?: number[];
  source_level_timeline?: number[];
  master_level_timeline?: number[];
  error_code?: string;
  error_message?: string;
  parent_job_id?: string;
  interactive_settings?: Record<string, number | boolean>;
}

export function isTerminalStatus(status: AnalysisJob["status"]): boolean {
  return status === "succeeded" || status === "failed";
}

export class AnalysisApiClient {
  public constructor(private readonly baseUrl = "/api/v1") {}

  public async submit(
    file: File,
    idempotencyKey: string,
    targetLufs = -14,
    bitDepth = 24,
    maximumGainAdjustmentDb = 12,
    ceilingDbfs = -1,
    masteringPassword = "",
    eqLowGainDb = 0,
    eqMidGainDb = 0,
    eqHighGainDb = 0,
    clipperDriveDb = 0,
    limiterLookaheadMs = 3,
    limiterReleaseMs = 80,
    highPassEnabled = true,
    highPassCutoffHz = 25,
    dynamicEqReductionDb = 0,
    bassControlReductionDb = 0,
    deEsserReductionDb = 0,
    saturationAmount = 0,
    aiAssistEnabled = false,
  ): Promise<AnalysisJob> {
    const body = new FormData();
    body.append("file", file);
    body.append("target_lufs", String(targetLufs));
    body.append("bit_depth", String(bitDepth));
    body.append("maximum_gain_adjustment_db", String(maximumGainAdjustmentDb));
    body.append("ceiling_dbfs", String(ceilingDbfs));
    body.append("eq_low_gain_db", String(eqLowGainDb));
    body.append("eq_mid_gain_db", String(eqMidGainDb));
    body.append("eq_high_gain_db", String(eqHighGainDb));
    body.append("clipper_drive_db", String(clipperDriveDb));
    body.append("limiter_lookahead_ms", String(limiterLookaheadMs));
    body.append("limiter_release_ms", String(limiterReleaseMs));
    body.append("high_pass_enabled", String(highPassEnabled));
    body.append("high_pass_cutoff_hz", String(highPassCutoffHz));
    body.append("dynamic_eq_reduction_db", String(dynamicEqReductionDb));
    body.append("bass_control_reduction_db", String(bassControlReductionDb));
    body.append("de_esser_reduction_db", String(deEsserReductionDb));
    body.append("saturation_amount", String(saturationAmount));
    body.append("ai_assist_enabled", String(aiAssistEnabled));
    body.append("mastering_password", masteringPassword);
    return this.request("/analysis-jobs", {
      method: "POST",
      body,
      headers: {
        "Idempotency-Key": idempotencyKey,
      },
    });
  }

  public async get(jobId: string): Promise<AnalysisJob> {
    return this.request(`/analysis-jobs/${encodeURIComponent(jobId)}`);
  }

  public async saveSettings(jobId: string, settings: Record<string, number | boolean>): Promise<AnalysisJob> {
    return this.request(`/analysis-jobs/${encodeURIComponent(jobId)}/settings`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ settings }),
    });
  }

  public async renderFinal(
    jobId: string,
    settings: Record<string, number | boolean>,
    password: string,
    idempotencyKey: string,
  ): Promise<AnalysisJob> {
    return this.request(`/analysis-jobs/${encodeURIComponent(jobId)}/final-renders`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Idempotency-Key": idempotencyKey },
      body: JSON.stringify({ settings, mastering_password: password }),
    });
  }

  private async request(path: string, init?: RequestInit): Promise<AnalysisJob> {
    const response = await fetch(`${this.baseUrl}${path}`, init);
    const contentType = response.headers.get("content-type") ?? "";
    if (!contentType.toLowerCase().includes("application/json")) {
      throw new Error(
        `Analysis API returned a non-JSON response (HTTP ${response.status}). Check the API route and ingress configuration.`,
      );
    }
    const payload = (await response.json()) as AnalysisJob | { detail?: string };
    if (!response.ok) {
      throw new Error("detail" in payload ? payload.detail ?? "Analysis request failed" : "Analysis request failed");
    }
    return payload as AnalysisJob;
  }
}

export function createIdempotencyKey(): string {
  return crypto.randomUUID();
}
