import { describe, expect, it } from "vitest";

import {
  backendSettings,
  masteringParameters,
  previewInputGainDb,
} from "./masteringParameters";

describe("interactive mastering metadata", () => {
  it("exposes every newly interactive delivery parameter to browser DSP", () => {
    for (const id of [
      "targetLufs",
      "maximumGainAdjustmentDb",
      "clipperDriveDb",
      "limiterLookaheadMs",
      "limiterReleaseMs",
      "saturationAmount",
      "bitDepth",
    ]) {
      const parameter = masteringParameters.find((candidate) => candidate.id === id);
      expect(parameter?.category).toBe("approximate");
      expect(parameter?.dsp).toBe("worklet");
    }
  });

  it("bounds preview loudness gain by the selected correction limit", () => {
    expect(previewInputGainDb(-9, -14, 12)).toBe(5);
    expect(previewInputGainDb(-8, -20, 6)).toBe(6);
    expect(previewInputGainDb(-24, -14, 4)).toBe(-4);
  });

  it("maps frontend values to the canonical backend fields", () => {
    expect(backendSettings({ clipperDriveDb: 2, bitDepth: 16 })).toMatchObject({
      clipper_drive_db: 2,
      bit_depth: 16,
    });
  });
});
