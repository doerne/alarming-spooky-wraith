import { useState } from "react";

import { DEFAULT_TREND_WEEKS, type TrendWeeks } from "@/shared/api/finding-trend";
import { FilterSummaryBar } from "@/shared/components/filter-summary-bar";
import { TrendCards } from "@/shared/components/trend-cards";
import { TrendChart } from "@/shared/components/trend-chart";
import { TrendRangeSelect } from "@/shared/components/trend-range-select";
import { describeScanFreshness } from "@/shared/lib/scan-freshness";

import { CvesTable } from "./components/cves-table";
import { IngestControl } from "./components/ingest-control";
import { SeverityChart } from "./components/severity-chart";
import { useFilteredFindings, useFindings } from "./hooks/use-findings";
import { useFindingTrend } from "./hooks/use-finding-trend";
import { isAlreadyRunning, useIngestStatus, useStartIngest } from "./hooks/use-run-ingest";
import {
  type ColumnOptions,
  DEFAULT_FILTERS,
  EMPTY_FILTERS,
  type FindingFilters,
  columnOptionsOf,
  emptyStateOf,
  hasActiveFilters,
} from "./model/filters";
import { severityCountsOf } from "./model/stats";
import type { FindingsPage } from "./model/types";

interface FilteredResultProps {
  page: FindingsPage | undefined;
  error: Error | null;
  filters: FindingFilters;
  options: ColumnOptions;
  onFiltersChange: (filters: FindingFilters) => void;
  onSelectCve: (advisoryId: string) => void;
}

/** Ergebnisbereich: Fehler oder Zusammenfassung + Tabelle mit Filtern im Kopf. */
function FilteredResult(props: FilteredResultProps) {
  const { page, error, filters, onFiltersChange } = props;
  const reset = () => onFiltersChange(EMPTY_FILTERS);
  if (error) {
    return (
      <p role="alert" className="text-destructive" data-testid="cves-error-findings">
        Funde konnten nicht geladen werden: {error.message}
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-2">
      {page ? (
        <FilterSummaryBar
          shown={page.total}
          total={page.unfilteredTotal}
          active={hasActiveFilters(filters)}
          feature="cves"
          onReset={reset}
        />
      ) : null}
      <CvesTable
        findings={page?.items ?? []}
        filters={filters}
        options={props.options}
        emptyState={emptyStateOf(page)}
        onFiltersChange={onFiltersChange}
        onReset={reset}
        onSelect={props.onSelectCve}
      />
    </div>
  );
}

export function CvesPage({ onSelectCve }: { onSelectCve: (advisoryId: string) => void }) {
  // Alle Funde liefern nur die Auswahlwerte der Spaltenfilter; Kacheln und Diagramme kommen aus dem Trend.
  const { data: findings = [] } = useFindings();
  const [weeks, setWeeks] = useState<TrendWeeks>(DEFAULT_TREND_WEEKS);
  const trend = useFindingTrend(weeks);
  const [filters, setFilters] = useState<FindingFilters>(DEFAULT_FILTERS);
  const filtered = useFilteredFindings(filters);
  const ingestStatus = useIngestStatus();
  const startIngest = useStartIngest();

  return (
    <section className="flex flex-col gap-6" data-testid="cves-section-overview">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Schwachstellen</h2>
        <IngestControl
          state={ingestStatus.data}
          alreadyRunning={isAlreadyRunning(startIngest.error)}
          freshness={
            ingestStatus.data
              ? describeScanFreshness({ status: ingestStatus.data, now: new Date() })
              : undefined
          }
          onStart={() => startIngest.mutate()}
        />
      </div>
      <TrendRangeSelect value={weeks} onChange={setWeeks} feature="cves" />
      {trend.data ? (
        <>
          <TrendCards trend={trend.data} feature="cves" />
          <div className="grid gap-6 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <TrendChart trend={trend.data} feature="cves" />
            </div>
            <SeverityChart data={severityCountsOf(trend.data.openBySeverityNow)} />
          </div>
        </>
      ) : null}
      <FilteredResult
        page={filtered.data}
        error={filtered.error}
        filters={filters}
        options={columnOptionsOf(findings)}
        onFiltersChange={setFilters}
        onSelectCve={onSelectCve}
      />
    </section>
  );
}
