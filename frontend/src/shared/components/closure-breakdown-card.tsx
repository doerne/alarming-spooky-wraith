import type { ClosedByOutcome } from "@/shared/api/finding-trend";
import { CLOSURE_KINDS, CLOSURE_KIND_LABELS } from "@/shared/api/remediation-kpis";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/card";

const CLOSURE_KIND_COLORS = {
  fixed_confirmed: "var(--chart-2)",
  fixed_reported: "var(--chart-1)",
  fixed_manual: "var(--chart-5)",
  accepted: "var(--muted-foreground)",
  false_positive: "color-mix(in oklch, var(--muted-foreground) 45%, transparent)",
} as const;

interface ClosureBreakdownCardProps {
  closedByOutcome: ClosedByOutcome;
  feature: string;
}

export function ClosureBreakdownCard({ closedByOutcome, feature }: ClosureBreakdownCardProps) {
  const total = CLOSURE_KINDS.reduce((sum, kind) => sum + closedByOutcome[kind], 0);

  return (
    <Card data-testid={`${feature}-card-closure-breakdown`}>
      <CardHeader>
        <CardTitle>Wie erledigt</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {total === 0 ? (
          <p className="text-sm text-muted-foreground">Im Zeitraum nichts erledigt.</p>
        ) : (
          <>
            <div
              className="flex h-3 w-full gap-px overflow-hidden rounded-full bg-background"
              aria-hidden
            >
              {CLOSURE_KINDS.filter((kind) => closedByOutcome[kind] > 0).map((kind) => (
                <div
                  key={kind}
                  data-testid={`${feature}-segment-closure-${kind.replaceAll("_", "-")}`}
                  style={{
                    width: `${(closedByOutcome[kind] / total) * 100}%`,
                    backgroundColor: CLOSURE_KIND_COLORS[kind],
                  }}
                />
              ))}
            </div>
            <ul className="space-y-1 text-sm">
              {CLOSURE_KINDS.map((kind) => (
                <li
                  key={kind}
                  className="flex items-center justify-between gap-2"
                  data-testid={`${feature}-item-closure-${kind.replaceAll("_", "-")}`}
                >
                  <span className="flex items-center gap-2">
                    <span
                      className="size-2 rounded-full"
                      style={{ backgroundColor: CLOSURE_KIND_COLORS[kind] }}
                      aria-hidden
                    />
                    {CLOSURE_KIND_LABELS[kind]}
                  </span>
                  <span className="font-medium">{closedByOutcome[kind]}</span>
                </li>
              ))}
            </ul>
          </>
        )}
      </CardContent>
    </Card>
  );
}
