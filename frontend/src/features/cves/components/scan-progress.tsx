import { Check, Circle, Loader2, Minus, X, type LucideIcon } from "lucide-react";

import { FINAL_SCAN_STEP_KEYS, type ScanStep, type ScanStepState } from "@/shared/api/scan-status";
import { cn } from "@/shared/lib/utils";

const FINISHED_STATES = new Set<ScanStepState>(["done", "skipped", "failed"]);
const PERCENT = 100;

const STATE_LABELS: Record<ScanStepState, string> = {
  pending: "wartet",
  running: "läuft",
  done: "erledigt",
  skipped: "übersprungen",
  failed: "fehlgeschlagen",
};

const STEP_ICONS: Record<ScanStepState, { icon: LucideIcon; className: string }> = {
  pending: { icon: Circle, className: "text-muted-foreground" },
  running: { icon: Loader2, className: "animate-spin" },
  done: { icon: Check, className: "" },
  skipped: { icon: Minus, className: "text-muted-foreground" },
  failed: { icon: X, className: "" },
};

interface ScanProgressProps {
  steps: ScanStep[];
}

function isFinished(step: ScanStep): boolean {
  return FINISHED_STATES.has(step.state);
}

function stateText(step: ScanStep): string {
  const label = STATE_LABELS[step.state];
  return step.detail ? `${label}: ${step.detail}` : label;
}

function percentFinished(steps: ScanStep[]): number {
  if (steps.length === 0) return 0;
  return Math.round((steps.filter(isFinished).length / steps.length) * PERCENT);
}

function StepChip({ step }: { step: ScanStep }) {
  const { icon: Icon, className } = STEP_ICONS[step.state];
  return (
    <li
      className={cn(
        "flex items-center gap-1 rounded-md border border-border px-2 py-0.5",
        step.state === "failed" && "text-destructive",
      )}
      title={step.detail || undefined}
      data-testid={`cves-item-scan-step-${step.key}`}
    >
      <Icon className={cn("size-3", className)} aria-hidden />
      {step.label}
      <span className="sr-only">({stateText(step)})</span>
    </li>
  );
}

/** Fortschritt des laufenden Scans: erledigte Quellen, Balken über alle Schritte, Schritt-Chips. */
export function ScanProgress({ steps }: ScanProgressProps) {
  const sources = steps.filter((step) => !FINAL_SCAN_STEP_KEYS.has(step.key));
  const summary = `${sources.filter(isFinished).length} von ${sources.length} Quellen erledigt`;
  const percent = percentFinished(steps);
  return (
    <div className="flex w-full flex-col gap-2" data-testid="cves-card-scan-progress">
      <p className="text-sm text-muted-foreground" data-testid="cves-text-scan-progress">
        Scan läuft · {summary}
      </p>
      <div
        role="progressbar"
        aria-label="Scan-Fortschritt"
        aria-valuemin={0}
        aria-valuemax={PERCENT}
        aria-valuenow={percent}
        aria-valuetext={summary}
        data-testid="cves-card-scan-bar"
        className="h-2 w-full overflow-hidden rounded-full bg-muted"
      >
        <div className="h-full bg-primary transition-all" style={{ width: `${percent}%` }} />
      </div>
      <ul className="flex flex-wrap gap-2 text-xs" data-testid="cves-list-scan-steps">
        {steps.map((step) => (
          <StepChip key={step.key} step={step} />
        ))}
      </ul>
    </div>
  );
}
