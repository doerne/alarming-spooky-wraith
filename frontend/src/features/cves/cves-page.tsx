import { useState } from "react";

import { FilterSummaryBar } from "@/shared/components/filter-summary-bar";
import { useDebouncedValue } from "@/shared/hooks/use-debounced-value";

import { CvesTable } from "./components/cves-table";
import { IngestControl } from "./components/ingest-control";
import { SectionCards } from "./components/section-cards";
import { SeverityChart } from "./components/severity-chart";
import { useFilteredFindings, useFindings } from "./hooks/use-findings";
import { isAlreadyRunning, useIngestStatus, useStartIngest } from "./hooks/use-run-ingest";
import {
  type ApplicationOption,
  EMPTY_FILTERS,
  type FindingFilters,
  applicationsOf,
  emptyStateOf,
  hasActiveFilters,
} from "./model/filters";
import { computeKpis, countBySeverity } from "./model/stats";
import type { FindingsPage } from "./model/types";

const SEARCH_DELAY_MS = 300;

interface FilteredResultProps {
  page: FindingsPage | undefined;
  error: Error | null;
  filters: FindingFilters;
  applications: ReadonlyArray<ApplicationOption>;
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
        applications={props.applications}
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
  // Suchfelder verzögert abfragen; Auswahlfilter wirken sofort.
  const advisoryQuery = useDebouncedValue(filters.advisoryQuery, SEARCH_DELAY_MS);
  const componentQuery = useDebouncedValue(filters.componentQuery, SEARCH_DELAY_MS);
  const filtered = useFilteredFindings({ ...filters, advisoryQuery, componentQuery });
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
        applications={applicationsOf(findings)}
        onFiltersChange={setFilters}
        onSelectCve={onSelectCve}
      />
    </section>
  );
}
