import { useState } from "react";

import { useDebouncedValue } from "@/shared/hooks/use-debounced-value";

import { ApplicationCvesPanel } from "./components/application-cves-panel";
import { useApplicationFindings } from "./hooks/use-application-findings";
import { type CveFilters, EMPTY_CVE_FILTERS } from "./model/cve-filters";

const SEARCH_DELAY_MS = 300;

interface ApplicationCvesPageProps {
  applicationId: number;
  onSelectCve: (advisoryId: string) => void;
}

/** Container des CVE-Reiters: Filterzustand + gefilterte Funde einer Anwendung. */
export function ApplicationCvesPage({ applicationId, onSelectCve }: ApplicationCvesPageProps) {
  const [filters, setFilters] = useState<CveFilters>(EMPTY_CVE_FILTERS);
  // Suchfelder verzögert abfragen; Auswahlfilter wirken sofort.
  const advisoryQuery = useDebouncedValue(filters.advisoryQuery, SEARCH_DELAY_MS);
  const componentQuery = useDebouncedValue(filters.componentQuery, SEARCH_DELAY_MS);
  const findings = useApplicationFindings(applicationId, {
    ...filters,
    advisoryQuery,
    componentQuery,
  });

  return (
    <div className="flex flex-col gap-4" data-testid="inventory-card-cves-panel">
      <ApplicationCvesPanel
        page={findings.data}
        filters={filters}
        onFiltersChange={setFilters}
        onSelectCve={onSelectCve}
      />
    </div>
  );
}
