import { describe, expect, it } from "vitest";

import {
  frequencyPercent,
  interpolateSeries,
  metric,
  meterPercent,
  movingPeakDensity,
  peakHeadroom,
  recommendationFindings,
  stageIndex,
  textMetric,
  transientActivity,
} from "./presentation";

describe("mastering result presentation", () => {
  it("maps durable job states to pipeline progress", () => {
    expect(stageIndex("queued")).toBe(0);
    expect(stageIndex("running")).toBe(1);
    expect(stageIndex("analyzed")).toBe(2);
    expect(stageIndex("mastering")).toBe(3);
    expect(stageIndex("succeeded")).toBe(4);
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

  it("bounds visual meter values", () => {
    expect(meterPercent({ phase: 0 }, "phase", -1, 1)).toBe(50);
    expect(meterPercent({ phase: 2 }, "phase", -1, 1)).toBe(100);
    expect(meterPercent(undefined, "phase", -1, 1)).toBe(0);
  });

  it("derives available peak headroom from the active ceiling", () => {
    expect(peakHeadroom({ peak_dbfs: -6 }, -1)).toBe("5.0 dB");
    expect(peakHeadroom({ peak_dbfs: -0.2 }, -1)).toBe("0.0 dB");
  });

  it("places the spectral centroid on a logarithmic audible-frequency axis", () => {
    expect(frequencyPercent({ spectral_centroid_hz: 20 })).toBe(0);
    expect(frequencyPercent({ spectral_centroid_hz: 20_000 })).toBe(100);
    expect(frequencyPercent({ spectral_centroid_hz: 2_000 })).toBeGreaterThan(50);
    expect(frequencyPercent(undefined)).toBe(0);
  });

  it("derives truthful compact comparison views from waveform envelopes", () => {
    expect(movingPeakDensity([0, 1, 0], 1)).toEqual([
      Math.sqrt(0.5),
      Math.sqrt(1 / 3),
      Math.sqrt(0.5),
    ]);
    expect(transientActivity([0, 0.5, 0.25])).toEqual([0, 0.5, 0.25]);
    expect(transientActivity([])).toEqual([]);
    expect(interpolateSeries([0, 1], [1, 0], 50)).toEqual([0.5, 0.5]);
    expect(interpolateSeries([0], [1], 150)).toEqual([1]);
  });
});
