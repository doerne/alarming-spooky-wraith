import { FilterSummaryBar } from "@/shared/components/filter-summary-bar";

import type { ApplicationFindingsPage } from "../api/inventory-api";
import { type CveFilters, EMPTY_CVE_FILTERS, hasActiveCveFilters } from "../model/cve-filters";
import { ApplicationCves } from "./application-cves";

interface ApplicationCvesPanelProps {
  page: ApplicationFindingsPage | undefined;
  filters: CveFilters;
  onFiltersChange: (filters: CveFilters) => void;
  onSelectCve: (advisoryId: string) => void;
}

/** Lädt: nichts; ohne Funde: Hinweis; sonst Zusammenfassung + Tabelle mit Kopf-Filtern. */
export function ApplicationCvesPanel({
  page,
  filters,
  onFiltersChange,
  onSelectCve,
}: ApplicationCvesPanelProps) {
  const reset = () => onFiltersChange(EMPTY_CVE_FILTERS);
  if (!page) return null;
  if (page.unfilteredTotal === 0) {
    return (
      <p className="text-sm text-muted-foreground" data-testid="inventory-text-no-cves">
        Keine Funde für diese Anwendung. Starte einen Scan auf der Schwachstellen-Seite.
      </p>
    );
  }
  return (
    <>
      <FilterSummaryBar
        shown={page.total}
        total={page.unfilteredTotal}
        active={hasActiveCveFilters(filters)}
        feature="inventory"
        onReset={reset}
      />
      <ApplicationCves
        findings={page.items}
        filters={filters}
        onFiltersChange={onFiltersChange}
        onReset={reset}
        onSelect={onSelectCve}
      />
    </>
  );
}
