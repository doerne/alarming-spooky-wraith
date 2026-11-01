import type { FilterOption } from "@/shared/components/multi-toggle-filter";

import type { RiskLevel } from "./types";

export interface FindingFilters {
  severities: RiskLevel[];
  statuses: string[];
  ecosystems: string[];
  applicationId: number | null;
  query: string;
}

export const EMPTY_FILTERS: FindingFilters = {
  severities: [],
  statuses: [],
  ecosystems: [],
  applicationId: null,
  query: "",
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
  return (
    filters.severities.length + filters.statuses.length + filters.ecosystems.length > 0 ||
    filters.applicationId !== null ||
    filters.query.trim() !== ""
  );
}
