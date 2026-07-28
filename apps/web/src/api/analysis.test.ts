import { describe, expect, it, vi } from "vitest";

import { AnalysisApiClient, isTerminalStatus } from "./analysis";

class FakeXMLHttpRequest {
  public static latest: FakeXMLHttpRequest | null = null;

  public readonly headers = new Map<string, string>();
  public readonly upload = {
    onprogress: null as ((event: ProgressEvent<EventTarget>) => void) | null,
    onload: null as (() => void) | null,
  };
  public method = "";
  public url = "";
  public sentBody: Document | XMLHttpRequestBodyInit | null = null;
  public status = 0;
  public responseText = "";
  public responseContentType = "application/json";
  public onabort: (() => void) | null = null;
  public onerror: (() => void) | null = null;
  public onload: (() => void) | null = null;

  public constructor() {
    FakeXMLHttpRequest.latest = this;
  }

  public open(method: string, url: string): void {
    this.method = method;
    this.url = url;
  }

  public setRequestHeader(name: string, value: string): void {
    this.headers.set(name, value);
  }

  public getResponseHeader(name: string): string | null {
    return name.toLowerCase() === "content-type" ? this.responseContentType : null;
  }

  public send(body: Document | XMLHttpRequestBodyInit | null): void {
    this.sentBody = body;
  }

  public abort(): void {
    this.onabort?.();
  }
}

describe("AnalysisApiClient", () => {
  it("authorizes before submitting an upload with the signed proof", async () => {
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
      "signed-proof",
    );

    expect(job.status).toBe("queued");
    expect(fetchMock).toHaveBeenCalledWith(
      "/v1/analysis-jobs",
      expect.objectContaining({
        headers: {
          "Idempotency-Key": "key-1",
          "X-Mastering-Authorization": "signed-proof",
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
    expect((request.body as FormData).get("ai_assist_enabled")).toBe("false");
    expect((request.body as FormData).has("mastering_password")).toBe(false);
  });

  it("returns a password error before any upload request is made", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "Invalid mastering password" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(new AnalysisApiClient("/v1").authorize("wrong")).rejects.toThrow(
      "Invalid mastering password",
    );
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/v1/mastering-access");
    const request = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect(request.body).toBe(JSON.stringify({ password: "wrong" }));
  });

  it("reports real multipart upload progress before the API accepts the job", async () => {
    vi.stubGlobal("XMLHttpRequest", FakeXMLHttpRequest);
    const progress: number[] = [];
    const submission = new AnalysisApiClient("/v1").submit(
      new File(["audio"], "mix.wav", { type: "audio/wav" }),
      "upload-key",
      -11,
      24,
      5,
      -1,
      "signed-proof",
      0,
      0,
      0,
      0,
      5,
      140,
      true,
      28,
      0.5,
      3,
      1,
      0,
      false,
      ({ percent }) => progress.push(percent),
    );
    const xhr = FakeXMLHttpRequest.latest;
    expect(xhr).not.toBeNull();
    if (!xhr) throw new Error("Expected an upload request");

    xhr.upload.onprogress?.({
      lengthComputable: true,
      loaded: 25,
      total: 100,
    } as ProgressEvent<EventTarget>);
    xhr.upload.onprogress?.({
      lengthComputable: true,
      loaded: 50,
      total: 100,
    } as ProgressEvent<EventTarget>);
    xhr.upload.onprogress?.({
      lengthComputable: true,
      loaded: 45,
      total: 100,
    } as ProgressEvent<EventTarget>);
    xhr.upload.onprogress?.({
      lengthComputable: false,
      loaded: 100,
      total: 0,
    } as ProgressEvent<EventTarget>);
    xhr.upload.onload?.();

    expect(progress).toEqual([25, 50, 50, 100]);
    expect(xhr.method).toBe("POST");
    expect(xhr.url).toBe("/v1/analysis-jobs");
    expect(xhr.headers.get("Idempotency-Key")).toBe("upload-key");
    expect(xhr.headers.get("X-Mastering-Authorization")).toBe("signed-proof");
    expect(xhr.headers.has("Content-Type")).toBe(false);
    expect((xhr.sentBody as FormData).get("target_lufs")).toBe("-11");
    expect((xhr.sentBody as FormData).get("bass_control_reduction_db")).toBe("3");

    xhr.status = 202;
    xhr.responseText = JSON.stringify({
      id: "job-uploaded",
      status: "queued",
      original_filename: "mix.wav",
    });
    xhr.onload?.();
    await expect(submission).resolves.toMatchObject({
      id: "job-uploaded",
      status: "queued",
    });
    xhr.upload.onprogress?.({
      lengthComputable: true,
      loaded: 100,
      total: 100,
    } as ProgressEvent<EventTarget>);
    expect(progress).toEqual([25, 50, 50, 100]);
  });

  it("surfaces a typed API rejection from the progress upload path", async () => {
    vi.stubGlobal("XMLHttpRequest", FakeXMLHttpRequest);
    const submission = new AnalysisApiClient("/v1").submit(
      new File(["audio"], "too-large.wav", { type: "audio/wav" }),
      "upload-key",
      -14,
      24,
      12,
      -1,
      "signed-proof",
      0,
      0,
      0,
      0,
      3,
      80,
      true,
      25,
      0,
      0,
      0,
      0,
      false,
      () => undefined,
    );
    const xhr = FakeXMLHttpRequest.latest;
    if (!xhr) throw new Error("Expected an upload request");
    xhr.status = 413;
    xhr.responseText = JSON.stringify({ detail: "Source exceeds MAX_UPLOAD_BYTES" });
    xhr.onload?.();

    await expect(submission).rejects.toThrow("Source exceeds MAX_UPLOAD_BYTES");
  });

  it("cancels an in-flight upload through its abort signal", async () => {
    vi.stubGlobal("XMLHttpRequest", FakeXMLHttpRequest);
    const controller = new AbortController();
    const submission = new AnalysisApiClient("/v1").submit(
      new File(["audio"], "mix.wav", { type: "audio/wav" }),
      "upload-key",
      -14,
      24,
      12,
      -1,
      "signed-proof",
      0,
      0,
      0,
      0,
      3,
      80,
      true,
      25,
      0,
      0,
      0,
      0,
      false,
      () => undefined,
      controller.signal,
    );

    controller.abort();

    await expect(submission).rejects.toMatchObject({ name: "AbortError" });
  });

  it("identifies terminal job states", () => {
    expect(isTerminalStatus("queued")).toBe(false);
    expect(isTerminalStatus("mastering")).toBe(false);
    expect(isTerminalStatus("analyzed")).toBe(true);
    expect(isTerminalStatus("succeeded")).toBe(true);
    expect(isTerminalStatus("failed")).toBe(true);
  });

  it("renames retained projects without uploading audio", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({
        id: "job-1",
        status: "analyzed",
        original_filename: "mix.wav",
        project_name: "Single final",
      }), { status: 200, headers: { "Content-Type": "application/json" } }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const renamed = await new AnalysisApiClient("/v1").rename("job-1", "Single final");

    expect(renamed.project_name).toBe("Single final");
    expect(fetchMock).toHaveBeenCalledWith("/v1/analysis-jobs/job-1", expect.objectContaining({
      method: "PATCH",
      body: JSON.stringify({ name: "Single final" }),
    }));
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
