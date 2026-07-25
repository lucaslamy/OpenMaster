import { describe, expect, it } from "vitest";

import {
  metric,
  recommendationFindings,
  stageIndex,
  textMetric,
} from "./presentation";

describe("mastering result presentation", () => {
  it("maps durable job states to pipeline progress", () => {
    expect(stageIndex("queued")).toBe(0);
    expect(stageIndex("running")).toBe(1);
    expect(stageIndex("mastering")).toBe(2);
    expect(stageIndex("succeeded")).toBe(3);
    expect(stageIndex("failed")).toBe(-1);
  });

  it("formats safe numeric and text measurements", () => {
    const result = { lufs: -13.842, musical_key: "A minor", unavailable: null };
    expect(metric(result, "lufs", " LUFS")).toBe("-13.8 LUFS");
    expect(metric(result, "unavailable")).toBe("—");
    expect(textMetric(result, "musical_key")).toBe("A minor");
    expect(textMetric(result, "unavailable")).toBe("—");
  });

  it("keeps only typed assistant findings", () => {
    expect(
      recommendationFindings({
        findings: [
          { code: "loudness", message: "Gain stays inside the safety policy." },
          { code: "invalid" },
          "not-a-finding",
        ],
      }),
    ).toEqual([
      { code: "loudness", message: "Gain stays inside the safety policy." },
    ]);
  });
});
