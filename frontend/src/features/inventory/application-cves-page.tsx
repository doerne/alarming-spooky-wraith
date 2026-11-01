import { useState } from "react";

import { ApplicationCvesPanel } from "./components/application-cves-panel";
import { useApplicationFindings } from "./hooks/use-application-findings";
import { type CveFilters, EMPTY_CVE_FILTERS, cveColumnOptionsOf } from "./model/cve-filters";

interface ApplicationCvesPageProps {
  applicationId: number;
  onSelectCve: (advisoryId: string) => void;
}

/** Container des CVE-Reiters: Filterzustand + gefilterte Funde einer Anwendung. */
export function ApplicationCvesPage({ applicationId, onSelectCve }: ApplicationCvesPageProps) {
  const [filters, setFilters] = useState<CveFilters>(EMPTY_CVE_FILTERS);
  const findings = useApplicationFindings(applicationId, filters);
  // Auswahlwerte für Advisory/Komponente aus allen Funden der Anwendung (ungefiltert).
  const allFindings = useApplicationFindings(applicationId, EMPTY_CVE_FILTERS);

  return (
    <div className="flex flex-col gap-4" data-testid="inventory-card-cves-panel">
      <ApplicationCvesPanel
        page={findings.data}
        options={cveColumnOptionsOf(allFindings.data?.items ?? [])}
        filters={filters}
        onFiltersChange={setFilters}
        onSelectCve={onSelectCve}
      />
    </div>
  );
}
