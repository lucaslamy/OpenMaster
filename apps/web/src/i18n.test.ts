import { describe, expect, it } from "vitest";

import {
  translate,
  translateApiError,
  translateFinding,
  translateMusicalKey,
} from "./i18n";

describe("bilingual interface catalogue", () => {
  it("provides technically accurate French mastering labels", () => {
    expect(translate("fr", "integratedLoudness")).toBe("Niveau sonore intégré");
    expect(translate("fr", "limiterCeiling")).toBe("Plafond du limiteur");
    expect(translate("fr", "phaseCorrelation")).toBe("Corrélation de phase");
    expect(translate("fr", "privateDownload", { depth: 24 })).toContain("24 bits");
  });

  it("translates structured assistant findings while preserving measurements", () => {
    expect(
      translateFinding(
        "fr",
        "loudness_target",
        "Integrated loudness is -13.8 LUFS; the requested target is -10.0 LUFS.",
      ),
    ).toContain("-13.8 LUFS");
    expect(translateFinding("en", "phase_warning", "Original message")).toBe(
      "Original message",
    );
  });

  it("localizes technical API errors and musical modes", () => {
    expect(
      translateApiError(
        "fr",
        "Analysis API returned a non-JSON response (HTTP 413). Check configuration.",
      ),
    ).toContain("HTTP 413");
    expect(translateMusicalKey("fr", "A minor")).toBe("A mineur");
    expect(translateMusicalKey("fr", "C major")).toBe("C majeur");
  });
});
