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

    const job = await new AnalysisApiClient("/v1").submit(
      file,
      "key-1",
      -14,
      24,
      12,
      -1,
      "secret",
    );

    expect(job.status).toBe("queued");
    expect(fetchMock).toHaveBeenCalledWith(
      "/v1/analysis-jobs",
      expect.objectContaining({
        headers: {
          "Idempotency-Key": "key-1",
          "X-Mastering-Password": "secret",
        },
        method: "POST",
      }),
    );
    const request = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect((request.body as FormData).get("target_lufs")).toBe("-14");
    expect((request.body as FormData).get("bit_depth")).toBe("24");
    expect((request.body as FormData).get("maximum_gain_adjustment_db")).toBe("12");
    expect((request.body as FormData).get("ceiling_dbfs")).toBe("-1");
    expect((request.body as FormData).get("eq_low_gain_db")).toBe("0");
    expect((request.body as FormData).get("clipper_drive_db")).toBe("0");
    expect((request.body as FormData).get("limiter_lookahead_ms")).toBe("3");
    expect((request.body as FormData).get("limiter_release_ms")).toBe("80");
    expect((request.body as FormData).get("high_pass_enabled")).toBe("true");
    expect((request.body as FormData).get("high_pass_cutoff_hz")).toBe("25");
    expect((request.body as FormData).get("dynamic_eq_reduction_db")).toBe("0");
    expect((request.body as FormData).get("bass_control_reduction_db")).toBe("0");
    expect((request.body as FormData).get("de_esser_reduction_db")).toBe("0");
    expect((request.body as FormData).get("saturation_amount")).toBe("0");
  });

  it("identifies terminal job states", () => {
    expect(isTerminalStatus("queued")).toBe(false);
    expect(isTerminalStatus("mastering")).toBe(false);
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
