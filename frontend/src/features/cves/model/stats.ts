import type { RiskLevel } from "./types";

export interface SeverityCount {
  level: RiskLevel;
  label: string;
  count: number;
}

// Feste Reihenfolge der Schweregrade von hoch nach niedrig.
const SEVERITY_ORDER: ReadonlyArray<{ level: RiskLevel; label: string }> = [
  { level: "kritisch", label: "Kritisch" },
  { level: "hoch", label: "Hoch" },
  { level: "mittel", label: "Mittel" },
  { level: "niedrig", label: "Niedrig" },
];

/** Offene Funde je Schweregrad in fester Reihenfolge (Eingabe: Trend-Antwort). */
export function severityCountsOf(openBySeverity: Record<RiskLevel, number>): SeverityCount[] {
  return SEVERITY_ORDER.map(({ level, label }) => ({
    level,
    label,
    count: openBySeverity[level],
  }));
}
