import { Loader2, Play } from "lucide-react";

import { Button } from "@/shared/ui/button";

import type { IngestState } from "../model/types";

interface IngestControlProps {
  state: IngestState | undefined;
  alreadyRunning: boolean;
  onStart: () => void;
}

function LastResult({ state }: { state: IngestState }) {
  if (state.error) {
    return (
      <span role="alert" className="text-sm text-destructive" data-testid="cves-error-ingest">
        {state.error}
      </span>
    );
  }
  if (!state.finishedAt || state.running) return null;
  return (
    <span className="text-sm text-muted-foreground" data-testid="cves-text-ingest-result">
      Letzter Scan: {state.findingsFound ?? 0} Funde
    </span>
  );
}

export function IngestControl({ state, alreadyRunning, onStart }: IngestControlProps) {
  const running = state?.running ?? false;
  return (
    <div className="flex flex-wrap items-center justify-end gap-3">
      {state ? <LastResult state={state} /> : null}
      {alreadyRunning ? (
        <span className="text-sm text-muted-foreground" data-testid="cves-text-ingest-running">
          Ein Scan läuft bereits
        </span>
      ) : null}
      <Button onClick={onStart} disabled={running} data-testid="cves-btn-run-ingest">
        {running ? <Loader2 className="animate-spin" aria-hidden /> : <Play aria-hidden />}
        {running ? "Scan läuft …" : "Scan starten"}
      </Button>
    </div>
  );
}
