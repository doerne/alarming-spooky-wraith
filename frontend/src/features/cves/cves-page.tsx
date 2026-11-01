import { useState } from "react";

import { FilterSummaryBar } from "@/shared/components/filter-summary-bar";

import { CvesTable } from "./components/cves-table";
import { IngestControl } from "./components/ingest-control";
import { SectionCards } from "./components/section-cards";
import { SeverityChart } from "./components/severity-chart";
import { useFilteredFindings, useFindings } from "./hooks/use-findings";
import { isAlreadyRunning, useIngestStatus, useStartIngest } from "./hooks/use-run-ingest";
import {
  type ColumnOptions,
  EMPTY_FILTERS,
  type FindingFilters,
  columnOptionsOf,
  emptyStateOf,
  hasActiveFilters,
} from "./model/filters";
import { computeKpis, countBySeverity } from "./model/stats";
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
  // Kacheln und Diagramm zeigen immer den Gesamtstand; nur die Tabelle wird gefiltert.
  const { data: findings = [] } = useFindings();
  const [filters, setFilters] = useState<FindingFilters>(EMPTY_FILTERS);
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
          onStart={() => startIngest.mutate()}
        />
      </div>
      <SectionCards kpis={computeKpis(findings)} />
      <SeverityChart data={countBySeverity(findings)} />
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
