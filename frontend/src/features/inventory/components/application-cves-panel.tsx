import { FilterSummaryBar } from "@/shared/components/filter-summary-bar";
import { ScanFreshness } from "@/shared/components/scan-freshness";
import type { ScanFreshnessView } from "@/shared/lib/scan-freshness";

import type { ApplicationFindingsPage } from "../api/inventory-api";
import {
  type CveColumnOptions,
  type CveFilters,
  EMPTY_CVE_FILTERS,
  hasActiveCveFilters,
} from "../model/cve-filters";
import { ApplicationCves } from "./application-cves";

interface ApplicationCvesPanelProps {
  page: ApplicationFindingsPage | undefined;
  filters: CveFilters;
  options: CveColumnOptions;
  freshness: ScanFreshnessView | undefined;
  onFiltersChange: (filters: CveFilters) => void;
  onSelectCve: (advisoryId: string) => void;
}

function Freshness({ freshness }: { freshness: ScanFreshnessView | undefined }) {
  if (!freshness) return null;
  return (
    <ScanFreshness
      text={freshness.text}
      warning={freshness.warning}
      testId="inventory-text-scan-freshness"
    />
  );
}

/** Stand der Daten; lädt: nichts; ohne Funde: Hinweis; sonst Zusammenfassung + Tabelle. */
export function ApplicationCvesPanel({ freshness, ...props }: ApplicationCvesPanelProps) {
  return (
    <>
      <Freshness freshness={freshness} />
      <CvesContent {...props} />
    </>
  );
}

function CvesContent({
  page,
  filters,
  options,
  onFiltersChange,
  onSelectCve,
}: Omit<ApplicationCvesPanelProps, "freshness">) {
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
        options={options}
        onFiltersChange={onFiltersChange}
        onReset={reset}
        onSelect={onSelectCve}
      />
    </>
  );
}
