import { useState } from "react";

import { ApplicationCvesPanel } from "./components/application-cves-panel";
import { CvesExportButton } from "./components/cves-export-button";
import { GithubCreateDialog } from "./components/github-create-dialog";
import { GithubSyncControls } from "./components/github-sync-controls";
import { useApplicationFindings } from "./hooks/use-application-findings";
import { useGithubSyncPanel } from "./hooks/use-github-sync-panel";
import { type CveFilters, EMPTY_CVE_FILTERS, cveColumnOptionsOf } from "./model/cve-filters";

interface ApplicationCvesPageProps {
  applicationId: number;
  onSelectCve: (advisoryId: string) => void;
}

/** Container des CVE-Reiters: Filterzustand, gefilterte Funde und GitHub-Anbindung. */
export function ApplicationCvesPage({ applicationId, onSelectCve }: ApplicationCvesPageProps) {
  const [filters, setFilters] = useState<CveFilters>(EMPTY_CVE_FILTERS);
  const findings = useApplicationFindings(applicationId, filters);
  // Auswahlwerte für Advisory/Komponente aus allen Funden der Anwendung (ungefiltert).
  const allFindings = useApplicationFindings(applicationId, EMPTY_CVE_FILTERS);
  const github = useGithubSyncPanel(applicationId);

  return (
    <div className="flex flex-col gap-4" data-testid="inventory-card-cves-panel">
      <div className="flex flex-wrap items-start justify-end gap-3">
        <CvesExportButton applicationId={applicationId} />
        <GithubSyncControls {...github.controls} />
      </div>
      {github.createOpen && (
        <GithubCreateDialog
          isStarting={github.isStarting}
          onConfirm={github.confirmCreate}
          onCancel={github.closeCreate}
        />
      )}
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
