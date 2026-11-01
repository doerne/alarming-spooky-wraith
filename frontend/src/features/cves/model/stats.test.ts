import { describe, expect, it } from "vitest";

import { computeKpis, countBySeverity } from "./stats";
import type { Finding } from "./types";

function makeFinding(overrides: Partial<Finding>): Finding {
  return {
    advisoryId: "GHSA-x",
    cveId: null,
    title: "Titel",
    applicationId: 1,
    applicationName: "App",
    componentId: 1,
    componentName: "Komponente",
    componentVersion: "1.0.0",
    ecosystem: null,
    riskScore: 0,
    riskLevel: "niedrig",
    fixVersion: null,
    status: "offen",
    ...overrides,
  };
}

describe("countBySeverity", () => {
  it("liefert alle vier Stufen in fester Reihenfolge, auch mit Anzahl null", () => {
    const result = countBySeverity([]);

    expect(result.map((entry) => entry.level)).toEqual(["kritisch", "hoch", "mittel", "niedrig"]);
    expect(result.every((entry) => entry.count === 0)).toBe(true);
  });

  it("zählt Funde je Schweregrad", () => {
    const findings = [
      makeFinding({ advisoryId: "a", riskLevel: "kritisch" }),
      makeFinding({ advisoryId: "b", riskLevel: "kritisch" }),
      makeFinding({ advisoryId: "c", riskLevel: "mittel" }),
    ];

    const byLevel = Object.fromEntries(countBySeverity(findings).map((e) => [e.level, e.count]));

    expect(byLevel).toEqual({ kritisch: 2, hoch: 0, mittel: 1, niedrig: 0 });
  });
});

describe("computeKpis", () => {
  it("summiert Gesamt, Kritisch, Hoch und Offen", () => {
    const findings = [
      makeFinding({ advisoryId: "a", riskLevel: "kritisch", status: "offen" }),
      makeFinding({ advisoryId: "b", riskLevel: "hoch", status: "behoben" }),
      makeFinding({ advisoryId: "c", riskLevel: "hoch", status: "offen" }),
      makeFinding({ advisoryId: "d", riskLevel: "niedrig", status: "akzeptiert" }),
    ];

    expect(computeKpis(findings)).toEqual({ total: 4, kritisch: 1, hoch: 2, offen: 2 });
  });
});
