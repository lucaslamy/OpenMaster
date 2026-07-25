import { describe, expect, it, vi } from "vitest";

import { AnalysisApiClient, isTerminalStatus } from "./analysis";

describe("AnalysisApiClient", () => {
  it("submits an upload with the idempotency key", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ id: "job-1", status: "queued" }), {
        status: 202,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const file = new File(["audio"], "mix.wav", { type: "audio/wav" });

    const job = await new AnalysisApiClient("/v1").submit(file, "key-1");

    expect(job.status).toBe("queued");
    expect(fetchMock).toHaveBeenCalledWith(
      "/v1/analysis-jobs",
      expect.objectContaining({ headers: { "Idempotency-Key": "key-1" }, method: "POST" }),
    );
  });

  it("identifies terminal job states", () => {
    expect(isTerminalStatus("queued")).toBe(false);
    expect(isTerminalStatus("succeeded")).toBe(true);
    expect(isTerminalStatus("failed")).toBe(true);
  });

  it("reports a routing error instead of parsing an HTML response as JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response("<!doctype html>", {
          status: 404,
          headers: { "Content-Type": "text/html" },
        }),
      ),
    );

    await expect(
      new AnalysisApiClient().submit(
        new File(["audio"], "mix.mp3", { type: "audio/mpeg" }),
        "key-2",
      ),
    ).rejects.toThrow("Analysis API returned a non-JSON response (HTTP 404)");
  });
});
