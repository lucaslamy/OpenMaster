/** Typed HTTP boundary for OpenMaster analysis-job operations. */

export interface AnalysisJob {
  id: string;
  status: "queued" | "running" | "analyzed" | "mastering" | "retry_wait" | "succeeded" | "failed";
  original_filename: string;
  project_name?: string;
  created_at?: string;
  updated_at?: string;
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
  source_preview_url?: string;
}

export interface UploadProgress {
  loadedBytes: number;
  totalBytes: number;
  percent: number;
}

export type UploadProgressHandler = (progress: UploadProgress) => void;

export function isTerminalStatus(status: AnalysisJob["status"]): boolean {
  return status === "analyzed" || status === "succeeded" || status === "failed";
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
    onUploadProgress?: UploadProgressHandler,
    signal?: AbortSignal,
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
    if (onUploadProgress || signal) {
      return this.upload(
        body,
        idempotencyKey,
        onUploadProgress,
        signal,
      );
    }
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

  public async listRecent(): Promise<AnalysisJob[]> {
    const response = await fetch(`${this.baseUrl}/analysis-jobs`);
    const payload = (await response.json()) as AnalysisJob[] | { detail?: string };
    if (!response.ok || !Array.isArray(payload)) {
      throw new Error(!Array.isArray(payload) ? payload.detail ?? "Project history failed" : "Project history failed");
    }
    return payload;
  }

  public async rename(jobId: string, name: string): Promise<AnalysisJob> {
    return this.request(`/analysis-jobs/${encodeURIComponent(jobId)}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
  }

  public async saveSettings(jobId: string, settings: Record<string, number | boolean>): Promise<AnalysisJob> {
    return this.request(`/analysis-jobs/${encodeURIComponent(jobId)}/settings`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ settings }),
    });
  }

  public async startMaster(
    jobId: string,
    settings: Record<string, number | boolean>,
  ): Promise<AnalysisJob> {
    return this.request(`/analysis-jobs/${encodeURIComponent(jobId)}/master`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ settings }),
    });
  }

  public async renderFinal(
    jobId: string,
    settings: Record<string, number | boolean>,
    idempotencyKey: string,
  ): Promise<AnalysisJob> {
    return this.request(`/analysis-jobs/${encodeURIComponent(jobId)}/final-renders`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": idempotencyKey,
      },
      body: JSON.stringify({ settings }),
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

  private upload(
    body: FormData,
    idempotencyKey: string,
    onProgress?: UploadProgressHandler,
    signal?: AbortSignal,
  ): Promise<AnalysisJob> {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      let lastPercent = 0;
      let lastLoadedBytes = 0;
      let lastTotalBytes = 0;
      let settled = false;

      const cleanup = (): void => {
        signal?.removeEventListener("abort", abortUpload);
      };
      const finish = (action: () => void): void => {
        if (settled) return;
        settled = true;
        cleanup();
        action();
      };
      const abortUpload = (): void => xhr.abort();

      xhr.open("POST", `${this.baseUrl}/analysis-jobs`);
      xhr.setRequestHeader("Idempotency-Key", idempotencyKey);
      xhr.upload.onprogress = (event: ProgressEvent<EventTarget>): void => {
        if (settled || !event.lengthComputable || event.total <= 0) return;
        const percent = Math.max(
          lastPercent,
          Math.min(100, Math.round((event.loaded / event.total) * 100)),
        );
        lastPercent = percent;
        lastLoadedBytes = Math.max(lastLoadedBytes, event.loaded);
        lastTotalBytes = Math.max(lastTotalBytes, event.total);
        onProgress?.({
          loadedBytes: lastLoadedBytes,
          totalBytes: lastTotalBytes,
          percent,
        });
      };
      xhr.upload.onload = (): void => {
        if (settled || lastPercent >= 100) return;
        lastPercent = 100;
        lastLoadedBytes = Math.max(lastLoadedBytes, lastTotalBytes);
        onProgress?.({
          loadedBytes: lastLoadedBytes,
          totalBytes: lastTotalBytes,
          percent: 100,
        });
      };
      xhr.onerror = (): void => {
        finish(() => reject(new Error("NetworkError when attempting to upload the source.")));
      };
      xhr.onabort = (): void => {
        finish(() => reject(new DOMException("Source upload cancelled", "AbortError")));
      };
      xhr.onload = (): void => {
        const contentType = xhr.getResponseHeader("content-type") ?? "";
        if (!contentType.toLowerCase().includes("application/json")) {
          finish(() => reject(new Error(
            `Analysis API returned a non-JSON response (HTTP ${xhr.status}). Check the API route and ingress configuration.`,
          )));
          return;
        }
        let payload: AnalysisJob | { detail?: string };
        try {
          payload = JSON.parse(xhr.responseText) as AnalysisJob | { detail?: string };
        } catch {
          finish(() => reject(new Error(
            `Analysis API returned a non-JSON response (HTTP ${xhr.status}). Check the API route and ingress configuration.`,
          )));
          return;
        }
        if (xhr.status < 200 || xhr.status >= 300) {
          finish(() => reject(new Error(
            "detail" in payload
              ? payload.detail ?? "Analysis request failed"
              : "Analysis request failed",
          )));
          return;
        }
        finish(() => resolve(payload as AnalysisJob));
      };

      if (signal?.aborted) {
        finish(() => reject(new DOMException("Source upload cancelled", "AbortError")));
        return;
      }
      signal?.addEventListener("abort", abortUpload, { once: true });
      xhr.send(body);
    });
  }
}

export function createIdempotencyKey(): string {
  return crypto.randomUUID();
}
