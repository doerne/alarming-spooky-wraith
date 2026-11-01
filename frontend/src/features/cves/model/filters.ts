import type { ColumnFilterOption as FilterOption } from "@/shared/components/column-filter";

import type { RiskLevel } from "./types";

export interface FindingFilters {
  severities: RiskLevel[];
  statuses: string[];
  ecosystems: string[];
  applicationIds: number[];
  advisoryQuery: string;
  componentQuery: string;
}

export const EMPTY_FILTERS: FindingFilters = {
  severities: [],
  statuses: [],
  ecosystems: [],
  applicationIds: [],
  advisoryQuery: "",
  componentQuery: "",
};

export const SEVERITY_OPTIONS: ReadonlyArray<FilterOption<RiskLevel>> = [
  { value: "kritisch", label: "Kritisch" },
  { value: "hoch", label: "Hoch" },
  { value: "mittel", label: "Mittel" },
  { value: "niedrig", label: "Niedrig" },
];

export const STATUS_OPTIONS: ReadonlyArray<FilterOption<string>> = [
  { value: "offen", label: "Offen" },
  { value: "in_arbeit", label: "In Arbeit" },
  { value: "akzeptiert", label: "Akzeptiert" },
  { value: "behoben", label: "Behoben" },
  { value: "false_positive", label: "False Positive" },
];

const ECOSYSTEMS = ["npm", "PyPI", "Maven", "Go", "crates.io", "RubyGems", "Packagist", "NuGet"];

/** "none" = Komponenten ohne Ökosystem (Produkte/Runtimes wie MariaDB, Redis). */
export const ECOSYSTEM_OPTIONS: ReadonlyArray<FilterOption<string>> = [
  ...ECOSYSTEMS.map((ecosystem) => ({ value: ecosystem, label: ecosystem })),
  { value: "none", label: "ohne" },
];

export function hasActiveFilters(filters: FindingFilters): boolean {
  const selected =
    filters.severities.length +
    filters.statuses.length +
    filters.ecosystems.length +
    filters.applicationIds.length;
  return selected > 0 || `${filters.advisoryQuery}${filters.componentQuery}`.trim() !== "";
}

export interface ApplicationOption {
  id: number;
  name: string;
}

/** Was die Tabelle ohne Zeilen zeigt: nichts (lädt), Filter-Hinweis oder Scan-Hinweis. */
export type EmptyState = "none" | "no-results" | "no-findings";

export function emptyStateOf(
  page: { total: number; unfilteredTotal: number } | undefined,
): EmptyState {
  if (!page || page.total > 0) return "none";
  return page.unfilteredTotal === 0 ? "no-findings" : "no-results";
}

/** Anwendungen aus den Funden, je einmal, alphabetisch (für den Anwendungsfilter). */
export function applicationsOf(
  findings: ReadonlyArray<{ applicationId: number; applicationName: string }>,
): ApplicationOption[] {
  const byId = new Map(findings.map((finding) => [finding.applicationId, finding.applicationName]));
  return [...byId].map(([id, name]) => ({ id, name })).sort((a, b) => a.name.localeCompare(b.name));
}
