import type { ColumnFilterOption as FilterOption } from "@/shared/components/column-filter";

import type { RiskLevel } from "./types";

export interface FindingFilters {
  severities: RiskLevel[];
  statuses: string[];
  ecosystems: string[];
  applicationIds: number[];
  advisoryIds: string[];
  componentNames: string[];
}

export const EMPTY_FILTERS: FindingFilters = {
  severities: [],
  statuses: [],
  ecosystems: [],
  applicationIds: [],
  advisoryIds: [],
  componentNames: [],
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
  const lists = [
    filters.severities,
    filters.statuses,
    filters.ecosystems,
    filters.applicationIds,
    filters.advisoryIds,
    filters.componentNames,
  ];
  return lists.some((values) => values.length > 0);
}

/** Auswahlwerte der Spaltenfilter, die aus den Daten stammen. */
export interface ColumnOptions {
  applications: ReadonlyArray<FilterOption<string>>;
  advisories: ReadonlyArray<FilterOption<string>>;
  components: ReadonlyArray<FilterOption<string>>;
}

function sortedOptions(entries: Iterable<[string, string]>): FilterOption<string>[] {
  return [...new Map(entries)]
    .map(([value, label]) => ({ value, label }))
    .sort((a, b) => a.label.localeCompare(b.label));
}

export function advisoryOptionsOf(
  findings: ReadonlyArray<{ advisoryId: string; cveId: string | null }>,
): FilterOption<string>[] {
  return sortedOptions(
    findings.map((finding) => [finding.advisoryId, finding.cveId ?? finding.advisoryId]),
  );
}

export function componentOptionsOf(
  findings: ReadonlyArray<{ componentName: string }>,
): FilterOption<string>[] {
  return sortedOptions(findings.map((finding) => [finding.componentName, finding.componentName]));
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

type OptionSource = { applicationId: number; applicationName: string } & {
  advisoryId: string;
  cveId: string | null;
  componentName: string;
};

/** Alle datengetriebenen Auswahlwerte der Spaltenfilter (aus den ungefilterten Funden). */
export function columnOptionsOf(findings: ReadonlyArray<OptionSource>): ColumnOptions {
  return {
    applications: applicationsOf(findings).map((app) => ({
      value: String(app.id),
      label: app.name,
    })),
    advisories: advisoryOptionsOf(findings),
    components: componentOptionsOf(findings),
  };
}
