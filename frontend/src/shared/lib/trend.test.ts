import { describe, expect, it } from "vitest";

import type { FindingTrend } from "@/shared/api/finding-trend";

import { hasMovement, openDeltaOf, openNowOf, weekLabelOf } from "./trend";

const base: FindingTrend = {
  weeks: [],
  openAtStart: 44,
  newTotal: 7,
  closedTotal: 12,
  closedByOutcome: {
    fixed_confirmed: 0,
    fixed_reported: 0,
    fixed_manual: 0,
    accepted: 0,
    false_positive: 0,
  },
  untouchedNow: 30,
  inProgressNow: 12,
  openBySeverityNow: { kritisch: 3, hoch: 10, mittel: 20, niedrig: 9 },
};

describe("trend", () => {
  it("summiert den aktuellen offenen Bestand", () => {
    expect(openNowOf(base)).toBe(42);
  });

  it("berechnet die Differenz zum Zeitraumbeginn", () => {
    expect(openDeltaOf(base)).toBe(-2);
  });

  it("formatiert den Wochenbeginn als TT.MM.", () => {
    expect(weekLabelOf("2026-11-16")).toBe("16.11.");
  });

  it("erkennt fehlende Bewegung", () => {
    const quiet = {
      ...base,
      weeks: [{ weekStart: "2026-11-16", new: 0, closed: 0, openAtEnd: 5 }],
    };
    expect(hasMovement(quiet)).toBe(false);
  });

  it("erkennt Bewegung durch neue oder erledigte Funde", () => {
    const moving = {
      ...base,
      weeks: [{ weekStart: "2026-11-16", new: 0, closed: 2, openAtEnd: 5 }],
    };
    expect(hasMovement(moving)).toBe(true);
  });
});
