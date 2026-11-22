import { useState } from "react";

import { DEFAULT_TREND_WEEKS, type TrendWeeks } from "@/shared/api/finding-trend";
import { TrendCards } from "@/shared/components/trend-cards";
import { TrendChart } from "@/shared/components/trend-chart";
import { TrendRangeSelect } from "@/shared/components/trend-range-select";
import { describeScanFreshness } from "@/shared/lib/scan-freshness";

import { ApplicationCvesPanel } from "./components/application-cves-panel";
import { CvesExportButton } from "./components/cves-export-button";
import { GithubCreateDialog } from "./components/github-create-dialog";
import { GithubSyncControls } from "./components/github-sync-controls";
import { useApplication } from "./hooks/use-application";
import { useApplicationFindings } from "./hooks/use-application-findings";
import { useApplicationTrend } from "./hooks/use-application-trend";
import { useGithubSyncPanel } from "./hooks/use-github-sync-panel";
import { useScanStatus } from "./hooks/use-scan-status";
import {
  type CveFilters,
  DEFAULT_CVE_FILTERS,
  EMPTY_CVE_FILTERS,
  cveColumnOptionsOf,
} from "./model/cve-filters";

interface ApplicationCvesPageProps {
  applicationId: number;
  onSelectCve: (advisoryId: string) => void;
}

/** Container des CVE-Reiters: Filterzustand, gefilterte Funde und GitHub-Anbindung. */
export function ApplicationCvesPage({ applicationId, onSelectCve }: ApplicationCvesPageProps) {
  const [filters, setFilters] = useState<CveFilters>(DEFAULT_CVE_FILTERS);
  const [weeks, setWeeks] = useState<TrendWeeks>(DEFAULT_TREND_WEEKS);
  const trend = useApplicationTrend(applicationId, weeks);
  const findings = useApplicationFindings(applicationId, filters);
  // Auswahlwerte für Advisory/Komponente aus allen Funden der Anwendung (ungefiltert).
  const allFindings = useApplicationFindings(applicationId, EMPTY_CVE_FILTERS);
  const github = useGithubSyncPanel(applicationId);
  const scanStatus = useScanStatus();
  const application = useApplication(applicationId);
  const freshness = scanStatus.data
    ? describeScanFreshness({
        status: scanStatus.data,
        now: new Date(),
        inventoryChangedAt: application.data?.inventoryChangedAt,
      })
    : undefined;

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
      <TrendRangeSelect value={weeks} onChange={setWeeks} feature="inventory" />
      {trend.isError && (
        <p role="alert" className="text-sm text-destructive" data-testid="inventory-error-trend">
          Verlauf konnte nicht geladen werden.
        </p>
      )}
      {trend.data && (
        <>
          <TrendCards trend={trend.data} feature="inventory" />
          <TrendChart trend={trend.data} feature="inventory" />
        </>
      )}
      <ApplicationCvesPanel
        page={findings.data}
        options={cveColumnOptionsOf(allFindings.data?.items ?? [])}
        filters={filters}
        freshness={freshness}
        onFiltersChange={setFilters}
        onSelectCve={onSelectCve}
      />
    </div>
  );
}
