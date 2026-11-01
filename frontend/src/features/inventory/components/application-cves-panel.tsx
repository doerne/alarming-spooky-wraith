import type { ApplicationFindingsPage } from "../api/inventory-api";
import { type CveFilters, EMPTY_CVE_FILTERS } from "../model/cve-filters";
import { ApplicationCveFilters } from "./application-cve-filters";
import { ApplicationCves } from "./application-cves";

interface ApplicationCvesPanelProps {
  page: ApplicationFindingsPage;
  filters: CveFilters;
  onFiltersChange: (filters: CveFilters) => void;
  onSelectCve: (advisoryId: string) => void;
}

/** Ohne Funde nur der Hinweis; sonst Filter und – wenn etwas übrig bleibt – die Tabelle. */
export function ApplicationCvesPanel({
  page,
  filters,
  onFiltersChange,
  onSelectCve,
}: ApplicationCvesPanelProps) {
  if (page.unfilteredTotal === 0) {
    return <ApplicationCves findings={[]} onSelect={onSelectCve} />;
  }
  return (
    <>
      <ApplicationCveFilters
        filters={filters}
        shown={page.total}
        total={page.unfilteredTotal}
        onChange={onFiltersChange}
        onReset={() => onFiltersChange(EMPTY_CVE_FILTERS)}
      />
      {page.total > 0 ? <ApplicationCves findings={page.items} onSelect={onSelectCve} /> : null}
    </>
  );
}
