import { Button } from "@/shared/ui/button";

import { CvesTable } from "./components/cves-table";
import { SectionCards } from "./components/section-cards";
import { SeverityChart } from "./components/severity-chart";
import { useFindings } from "./hooks/use-findings";
import { useRunIngest } from "./hooks/use-run-ingest";
import { computeKpis, countBySeverity } from "./model/stats";

export function CvesPage() {
  const { data: findings = [] } = useFindings();
  const ingest = useRunIngest();

  return (
    <section className="flex flex-col gap-6" data-testid="cves-section-overview">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Schwachstellen</h2>
        <Button
          onClick={() => ingest.mutate()}
          disabled={ingest.isPending}
          data-testid="cves-btn-run-ingest"
        >
          Scan starten
        </Button>
      </div>
      <SectionCards kpis={computeKpis(findings)} />
      <SeverityChart data={countBySeverity(findings)} />
      <CvesTable findings={findings} />
    </section>
  );
}
