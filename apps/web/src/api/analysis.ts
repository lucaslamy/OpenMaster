/** Typed HTTP boundary for OpenMaster analysis-job operations. */

export interface AnalysisJob {
  id: string;
  status: "queued" | "running" | "retry_wait" | "succeeded" | "failed";
  result?: Record<string, unknown>;
  error_code?: string;
  error_message?: string;
}

export function isTerminalStatus(status: AnalysisJob["status"]): boolean {
  return status === "succeeded" || status === "failed";
}

export class AnalysisApiClient {
  public constructor(private readonly baseUrl = "/api/v1") {}

  public async submit(file: File, idempotencyKey: string): Promise<AnalysisJob> {
    const body = new FormData();
    body.append("file", file);
    return this.request("/analysis-jobs", {
      method: "POST",
      body,
      headers: { "Idempotency-Key": idempotencyKey },
    });
  }

  public async get(jobId: string): Promise<AnalysisJob> {
    return this.request(`/analysis-jobs/${encodeURIComponent(jobId)}`);
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
