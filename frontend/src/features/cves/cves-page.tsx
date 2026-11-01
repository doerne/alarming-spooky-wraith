import { CvesTable } from "./components/cves-table";
import { SectionCards } from "./components/section-cards";
import { SeverityChart } from "./components/severity-chart";
import { useFindings } from "./hooks/use-findings";
import { IngestControl } from "./components/ingest-control";
import { isAlreadyRunning, useIngestStatus, useStartIngest } from "./hooks/use-run-ingest";
import { computeKpis, countBySeverity } from "./model/stats";

export function CvesPage() {
  const { data: findings = [] } = useFindings();
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
      <CvesTable findings={findings} />
    </section>
  );
}
