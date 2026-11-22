import { Loader2, Play } from "lucide-react";

import type { ScanStatus } from "@/shared/api/scan-status";
import { ScanFreshness } from "@/shared/components/scan-freshness";
import type { ScanFreshnessView } from "@/shared/lib/scan-freshness";
import { Button } from "@/shared/ui/button";

import { ScanProgress } from "./scan-progress";

interface IngestControlProps {
  state: ScanStatus | undefined;
  alreadyRunning: boolean;
  freshness: ScanFreshnessView | undefined;
  onStart: () => void;
}

function LastError({ state }: { state: ScanStatus }) {
  if (!state.error) return null;
  return (
    <span role="alert" className="text-sm text-destructive" data-testid="cves-error-ingest">
      {state.error}
    </span>
  );
}

/** Fortschritt nur während eines Laufs und erst, wenn das Backend Schritte meldet. */
function RunningProgress({ state }: { state: ScanStatus | undefined }) {
  if (!state?.running || state.steps.length === 0) return null;
  return <ScanProgress steps={state.steps} />;
}

export function IngestControl({ state, alreadyRunning, freshness, onStart }: IngestControlProps) {
  const running = state?.running ?? false;
  return (
    <div className="flex flex-wrap items-center justify-end gap-3">
      {freshness ? (
        <ScanFreshness
          text={freshness.text}
          warning={freshness.warning}
          testId="cves-text-scan-freshness"
        />
      ) : null}
      {state ? <LastError state={state} /> : null}
      {alreadyRunning ? (
        <span className="text-sm text-muted-foreground" data-testid="cves-text-ingest-running">
          Ein Scan läuft bereits
        </span>
      ) : null}
      <Button onClick={onStart} disabled={running} data-testid="cves-btn-run-ingest">
        {running ? <Loader2 className="animate-spin" aria-hidden /> : <Play aria-hidden />}
        {running ? "Scan läuft …" : "Scan starten"}
      </Button>
      <RunningProgress state={state} />
    </div>
  );
}
