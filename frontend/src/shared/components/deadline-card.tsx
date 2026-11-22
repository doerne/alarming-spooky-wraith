import type { RemediationKpis } from "@/shared/api/remediation-kpis";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/card";

interface DeadlineCardProps {
  deadlines: RemediationKpis["deadlines"];
  openTotal: number;
  feature: string;
}

/** ISO-Zeitstempel → „05.12.“ in lokaler Zeit */
function dayLabelOf(isoDateTime: string): string {
  const date = new Date(isoDateTime);
  const day = String(date.getDate()).padStart(2, "0");
  const month = String(date.getMonth() + 1).padStart(2, "0");
  return `${day}.${month}.`;
}

function Figure({ label, value, testId, className }: FigureProps) {
  return (
    <div>
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className={`text-3xl font-semibold ${className}`} data-testid={testId}>
        {value}
      </p>
    </div>
  );
}

interface FigureProps {
  label: string;
  value: string | number;
  testId: string;
  className?: string;
}

export function DeadlineCard({ deadlines, openTotal, feature }: DeadlineCardProps) {
  const overdueClass = deadlines.overdue > 0 ? "text-destructive" : "";

  return (
    <Card data-testid={`${feature}-card-deadlines`}>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-muted-foreground">Fristen</CardTitle>
      </CardHeader>
      <CardContent>
        {openTotal === 0 ? (
          <p className="text-sm text-muted-foreground">Keine offenen Funde.</p>
        ) : (
          <div className="grid grid-cols-3 gap-4">
            <Figure
              label="Überfällig"
              value={deadlines.overdue}
              testId={`${feature}-text-overdue`}
              className={overdueClass}
            />
            <Figure
              label="Bald fällig"
              value={deadlines.dueSoon}
              testId={`${feature}-text-due-soon`}
            />
            <Figure
              label="Nächste Frist"
              value={deadlines.nextDueAt === null ? "–" : dayLabelOf(deadlines.nextDueAt)}
              testId={`${feature}-text-next-due`}
            />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
