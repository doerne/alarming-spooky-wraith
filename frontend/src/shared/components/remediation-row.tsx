import type { FindingTrend } from "@/shared/api/finding-trend";
import type { RemediationKpis } from "@/shared/api/remediation-kpis";
import { ClosureBreakdownCard } from "@/shared/components/closure-breakdown-card";
import { DeadlineCard } from "@/shared/components/deadline-card";
import { UpdateTargetsCard } from "@/shared/components/update-targets-card";

interface RemediationRowProps {
  kpis: RemediationKpis | undefined;
  kpisFailed: boolean;
  trend: FindingTrend | undefined;
  feature: string;
  showApplications: boolean;
}

/** Reihe mit Fristen, Erledigungsarten und Update-Zielen; jede Karte erscheint, sobald ihre Daten da sind. */
export function RemediationRow(props: RemediationRowProps) {
  const { kpis, kpisFailed, trend, feature, showApplications } = props;
  return (
    <>
      {kpisFailed && (
        <p role="alert" className="text-sm text-destructive" data-testid={`${feature}-error-kpis`}>
          Kennzahlen konnten nicht geladen werden.
        </p>
      )}
      {(kpis || trend) && (
        <div className="grid gap-6 lg:grid-cols-3">
          {kpis && (
            <DeadlineCard
              deadlines={kpis.deadlines}
              openTotal={kpis.updates.openTotal}
              feature={feature}
            />
          )}
          {trend && (
            <ClosureBreakdownCard closedByOutcome={trend.closedByOutcome} feature={feature} />
          )}
          {kpis && (
            <UpdateTargetsCard
              updates={kpis.updates}
              feature={feature}
              showApplications={showApplications}
            />
          )}
        </div>
      )}
    </>
  );
}
