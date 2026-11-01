import { useState } from "react";

import { useDebouncedValue } from "@/shared/hooks/use-debounced-value";

import type { ApplicationFindingsPage } from "./api/inventory-api";
import { ApplicationCveFilters } from "./components/application-cve-filters";
import { ApplicationCves } from "./components/application-cves";
import { useApplicationFindings } from "./hooks/use-application-findings";
import { type CveFilters, EMPTY_CVE_FILTERS } from "./model/cve-filters";

const SEARCH_DELAY_MS = 300;
const EMPTY_PAGE: ApplicationFindingsPage = { items: [], total: 0, unfilteredTotal: 0 };

interface ApplicationCvesPageProps {
  applicationId: number;
  onSelectCve: (advisoryId: string) => void;
}

interface CvesContentProps {
  page: ApplicationFindingsPage;
  filters: CveFilters;
  onFiltersChange: (filters: CveFilters) => void;
  onSelectCve: (advisoryId: string) => void;
}

/** Ohne Funde nur der Hinweis; sonst Filter und – wenn etwas übrig bleibt – die Tabelle. */
function CvesContent({ page, filters, onFiltersChange, onSelectCve }: CvesContentProps) {
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

/** Container des CVE-Reiters: Filterzustand + gefilterte Funde einer Anwendung. */
export function ApplicationCvesPage({ applicationId, onSelectCve }: ApplicationCvesPageProps) {
  const [filters, setFilters] = useState<CveFilters>(EMPTY_CVE_FILTERS);
  const query = useDebouncedValue(filters.query, SEARCH_DELAY_MS);
  const findings = useApplicationFindings(applicationId, { ...filters, query });

  return (
    <div className="flex flex-col gap-4">
      <CvesContent
        page={findings.data ?? EMPTY_PAGE}
        filters={filters}
        onFiltersChange={setFilters}
        onSelectCve={onSelectCve}
      />
    </div>
  );
}
