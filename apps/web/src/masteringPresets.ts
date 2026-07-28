/** Reproducible mastering starting points shared by the studio presentation. */

export interface MasteringIntent {
  key: string;
  copy: string;
  target: number;
  ceiling: number;
  gain: number;
  depth: number;
  eq: readonly [number, number, number];
  clip: number;
  spectral: readonly [number, number, number, number];
  highPassEnabled: boolean;
  highPassCutoffHz: number;
  limiterLookaheadMs: number;
  limiterReleaseMs: number;
  aiAssistEnabled: boolean;
  featured?: boolean;
}

const standardTiming = {
  highPassEnabled: true,
  highPassCutoffHz: 25,
  limiterLookaheadMs: 3,
  limiterReleaseMs: 80,
  aiAssistEnabled: false,
} as const;

export const masteringIntents = [
  {
    ...standardTiming,
    key: "Transparent",
    copy: "Transparent",
    target: -16,
    ceiling: -1.5,
    gain: 6,
    depth: 24,
    eq: [0, 0, 0],
    clip: 0,
    spectral: [0, 0, 0, 0],
  },
  {
    ...standardTiming,
    key: "Streaming",
    copy: "Streaming",
    target: -14,
    ceiling: -1,
    gain: 9,
    depth: 24,
    eq: [0, 0, 0],
    clip: 1,
    spectral: [1.5, 1.5, 1.5, 0.1],
  },
  {
    ...standardTiming,
    key: "Podcast",
    copy: "Podcast",
    target: -16,
    ceiling: -1,
    gain: 6,
    depth: 16,
    eq: [-0.5, 1, 0.5],
    clip: 1,
    spectral: [2, 1, 4, 0.1],
  },
  {
    ...standardTiming,
    key: "Rap",
    copy: "Rap",
    target: -10,
    ceiling: -1,
    gain: 10,
    depth: 24,
    eq: [0.5, 0.5, 0.75],
    clip: 1,
    spectral: [0.5, 2.5, 1.5, 0.04],
  },
  {
    ...standardTiming,
    key: "RapReloaded",
    copy: "RapReloaded",
    target: -10.5,
    ceiling: -1,
    gain: 6,
    depth: 24,
    eq: [0, 0.25, 0.25],
    clip: 0,
    spectral: [0.5, 0, 0.5, 0],
    highPassCutoffHz: 20,
    limiterLookaheadMs: 5,
    limiterReleaseMs: 70,
    featured: true,
  },
  {
    ...standardTiming,
    key: "Club",
    copy: "Club",
    target: -10,
    ceiling: -0.5,
    gain: 10,
    depth: 24,
    eq: [0.5, -0.5, 1],
    clip: 3,
    spectral: [2, 5, 2, 0.08],
  },
  {
    ...standardTiming,
    key: "Loud",
    copy: "Loud",
    target: -10,
    ceiling: -0.5,
    gain: 12,
    depth: 24,
    eq: [0.5, 0, 0.5],
    clip: 5,
    spectral: [3, 3, 3, 0.25],
  },
  {
    ...standardTiming,
    key: "Dynamic",
    copy: "Dynamic",
    target: -18,
    ceiling: -2,
    gain: 5,
    depth: 24,
    eq: [0, 0, 0],
    clip: 0,
    spectral: [0, 0, 0, 0],
  },
] as const satisfies readonly MasteringIntent[];
