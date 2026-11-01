import { CvesTable } from "./components/cves-table";
import { SectionCards } from "./components/section-cards";
import { SeverityChart } from "./components/severity-chart";
import { useState } from "react";

import { useDebouncedValue } from "@/shared/hooks/use-debounced-value";

import { FilterSummary } from "./components/filter-summary";
import { FindingsFilterBar } from "./components/findings-filter-bar";
import { useFilteredFindings, useFindings } from "./hooks/use-findings";
import { EMPTY_FILTERS, type FindingFilters } from "./model/filters";
import type { Finding } from "./model/types";
import { IngestControl } from "./components/ingest-control";
import { isAlreadyRunning, useIngestStatus, useStartIngest } from "./hooks/use-run-ingest";
import { computeKpis, countBySeverity } from "./model/stats";

const SEARCH_DELAY_MS = 300;

function applicationsOf(findings: Finding[]): { id: number; name: string }[] {
  const byId = new Map(findings.map((finding) => [finding.applicationId, finding.applicationName]));
  return [...byId].map(([id, name]) => ({ id, name })).sort((a, b) => a.name.localeCompare(b.name));
}

export function CvesPage({ onSelectCve }: { onSelectCve: (advisoryId: string) => void }) {
  // Kacheln und Diagramm zeigen immer den Gesamtstand; nur die Tabelle wird gefiltert.
  const { data: findings = [] } = useFindings();
  const [filters, setFilters] = useState<FindingFilters>(EMPTY_FILTERS);
  const query = useDebouncedValue(filters.query, SEARCH_DELAY_MS);
  const filtered = useFilteredFindings({ ...filters, query });
  const page = filtered.data;
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
      <FindingsFilterBar
        filters={filters}
        applications={applicationsOf(findings)}
        onChange={setFilters}
        onReset={() => setFilters(EMPTY_FILTERS)}
      />
      {page ? <FilterSummary shown={page.total} total={page.unfilteredTotal} /> : null}
      <CvesTable findings={page?.items ?? []} onSelect={onSelectCve} />
    </section>
  );
}
