import { useState } from "react";

import { useDebouncedValue } from "@/shared/hooks/use-debounced-value";

import { CvesTable } from "./components/cves-table";
import { FilterSummary } from "./components/filter-summary";
import { FindingsFilterBar } from "./components/findings-filter-bar";
import { IngestControl } from "./components/ingest-control";
import { SectionCards } from "./components/section-cards";
import { SeverityChart } from "./components/severity-chart";
import { useFilteredFindings, useFindings } from "./hooks/use-findings";
import { isAlreadyRunning, useIngestStatus, useStartIngest } from "./hooks/use-run-ingest";
import { EMPTY_FILTERS, type FindingFilters, applicationsOf } from "./model/filters";
import { computeKpis, countBySeverity } from "./model/stats";
import type { FindingsPage } from "./model/types";

const SEARCH_DELAY_MS = 300;

interface FilteredResultProps {
  page: FindingsPage | undefined;
  error: Error | null;
  onReset: () => void;
  onSelectCve: (advisoryId: string) => void;
}

/** Ergebnisbereich: Fehler, Hinweis bei 0 Treffern oder Zusammenfassung + Tabelle. */
function FilteredResult({ page, error, onReset, onSelectCve }: FilteredResultProps) {
  if (error) {
    return (
      <p role="alert" className="text-destructive" data-testid="cves-error-findings">
        Funde konnten nicht geladen werden: {error.message}
      </p>
    );
  }
  if (!page) return null;
  return (
    <>
      <FilterSummary shown={page.total} total={page.unfilteredTotal} onReset={onReset} />
      {page.total > 0 || page.unfilteredTotal === 0 ? (
        <CvesTable findings={page.items} onSelect={onSelectCve} />
      ) : null}
    </>
  );
}

export function CvesPage({ onSelectCve }: { onSelectCve: (advisoryId: string) => void }) {
  // Kacheln und Diagramm zeigen immer den Gesamtstand; nur die Tabelle wird gefiltert.
  const { data: findings = [] } = useFindings();
  const [filters, setFilters] = useState<FindingFilters>(EMPTY_FILTERS);
  const query = useDebouncedValue(filters.query, SEARCH_DELAY_MS);
  const filtered = useFilteredFindings({ ...filters, query });
  const ingestStatus = useIngestStatus();
  const startIngest = useStartIngest();
  const reset = () => setFilters(EMPTY_FILTERS);

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
      <FindingsFilterBar
        filters={filters}
        applications={applicationsOf(findings)}
        onChange={setFilters}
        onReset={reset}
      />
      <FilteredResult
        page={filtered.data}
        error={filtered.error}
        onReset={reset}
        onSelectCve={onSelectCve}
      />
    </section>
  );
}
