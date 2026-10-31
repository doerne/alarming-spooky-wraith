import { Button } from "@/shared/ui/button";

import { CvesTable } from "./components/cves-table";
import { useFindings } from "./hooks/use-findings";
import { useRunIngest } from "./hooks/use-run-ingest";

export function CvesPage() {
  const { data: findings = [] } = useFindings();
  const ingest = useRunIngest();
  return (
    <section className="w-full" data-testid="cves-section-overview">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">Schwachstellen</h2>
        <Button
          onClick={() => ingest.mutate()}
          disabled={ingest.isPending}
          data-testid="cves-btn-run-ingest"
        >
          Scan starten
        </Button>
      </div>
      <CvesTable findings={findings} />
    </section>
  );
}
