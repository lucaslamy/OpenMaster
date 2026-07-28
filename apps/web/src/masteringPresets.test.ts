import { describe, expect, it } from "vitest";

import { masteringIntents } from "./masteringPresets";

describe("mastering presets", () => {
  it("keeps the existing Rap preset unchanged", () => {
    expect(masteringIntents.find(({ key }) => key === "Rap")).toMatchObject({
      target: -10,
      ceiling: -1,
      gain: 10,
      depth: 24,
      eq: [0.5, 0.5, 0.75],
      clip: 1,
      spectral: [0.5, 2.5, 1.5, 0.04],
      highPassEnabled: true,
      highPassCutoffHz: 25,
      limiterLookaheadMs: 3,
      limiterReleaseMs: 80,
      aiAssistEnabled: false,
    });
  });

  it("defines Rap Reloaded as a conservative bass-safe preset", () => {
    expect(masteringIntents.find(({ key }) => key === "RapReloaded")).toMatchObject({
      target: -10.5,
      ceiling: -1,
      gain: 6,
      depth: 24,
      eq: [0, 0.25, 0.25],
      clip: 0,
      spectral: [0.5, 0, 0.5, 0],
      highPassEnabled: true,
      highPassCutoffHz: 20,
      limiterLookaheadMs: 5,
      limiterReleaseMs: 70,
      aiAssistEnabled: false,
    });
  });

  it("keeps every preset key unique and every control inside renderer bounds", () => {
    const keys = masteringIntents.map(({ key }) => key);
    expect(new Set(keys).size).toBe(keys.length);

    for (const intent of masteringIntents) {
      expect(intent.target).toBeGreaterThanOrEqual(-24);
      expect(intent.target).toBeLessThanOrEqual(-8);
      expect(intent.ceiling).toBeGreaterThanOrEqual(-6);
      expect(intent.ceiling).toBeLessThanOrEqual(-0.1);
      expect(intent.gain).toBeGreaterThanOrEqual(0);
      expect(intent.gain).toBeLessThanOrEqual(12);
      expect([16, 24, 32]).toContain(intent.depth);
      intent.eq.forEach((gain) => {
        expect(gain).toBeGreaterThanOrEqual(-6);
        expect(gain).toBeLessThanOrEqual(6);
      });
      expect(intent.clip).toBeGreaterThanOrEqual(0);
      expect(intent.clip).toBeLessThanOrEqual(12);
      intent.spectral.slice(0, 3).forEach((reduction) => {
        expect(reduction).toBeGreaterThanOrEqual(0);
        expect(reduction).toBeLessThanOrEqual(12);
      });
      expect(intent.spectral[3]).toBeGreaterThanOrEqual(0);
      expect(intent.spectral[3]).toBeLessThanOrEqual(1);
      expect(intent.highPassCutoffHz).toBeGreaterThanOrEqual(15);
      expect(intent.highPassCutoffHz).toBeLessThanOrEqual(80);
      expect(intent.limiterLookaheadMs).toBeGreaterThanOrEqual(0);
      expect(intent.limiterLookaheadMs).toBeLessThanOrEqual(10);
      expect(intent.limiterReleaseMs).toBeGreaterThanOrEqual(10);
      expect(intent.limiterReleaseMs).toBeLessThanOrEqual(500);
    }
  });
});
