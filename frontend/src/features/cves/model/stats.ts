import type { Finding, RiskLevel } from "./types";

export interface SeverityCount {
  level: RiskLevel;
  label: string;
  count: number;
}

export interface CveKpis {
  total: number;
  kritisch: number;
  hoch: number;
  offen: number;
}

// Feste Reihenfolge der Schweregrade von hoch nach niedrig.
const SEVERITY_ORDER: ReadonlyArray<{ level: RiskLevel; label: string }> = [
  { level: "kritisch", label: "Kritisch" },
  { level: "hoch", label: "Hoch" },
  { level: "mittel", label: "Mittel" },
  { level: "niedrig", label: "Niedrig" },
];

function countLevel(findings: Finding[], level: RiskLevel): number {
  return findings.filter((finding) => finding.riskLevel === level).length;
}

export function countBySeverity(findings: Finding[]): SeverityCount[] {
  return SEVERITY_ORDER.map(({ level, label }) => ({
    level,
    label,
    count: countLevel(findings, level),
  }));
}

export function computeKpis(findings: Finding[]): CveKpis {
  return {
    total: findings.length,
    kritisch: countLevel(findings, "kritisch"),
    hoch: countLevel(findings, "hoch"),
    offen: findings.filter((finding) => finding.status === "offen").length,
  };
}
