import { Minus, TrendingDown, TrendingUp, type LucideIcon } from "lucide-react";

import type { FindingTrend } from "@/shared/api/finding-trend";
import { openDeltaOf, openNowOf } from "@/shared/lib/trend";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/card";

interface DeltaDisplay {
  text: string;
  Icon: LucideIcon;
  colorClass: string;
}

function deltaDisplayOf(delta: number): DeltaDisplay {
  if (delta > 0) {
    return { text: `+${delta}`, Icon: TrendingUp, colorClass: "text-destructive" };
  }
  if (delta < 0) {
    return { text: `−${Math.abs(delta)}`, Icon: TrendingDown, colorClass: "text-primary" };
  }
  return { text: "±0", Icon: Minus, colorClass: "text-muted-foreground" };
}

function StatCard({ title, value, testId }: { title: string; value: number; testId: string }) {
  return (
    <Card data-testid={testId}>
      <CardHeader>
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="text-3xl font-semibold">{value}</p>
      </CardContent>
    </Card>
  );
}

export function TrendCards({ trend, feature }: { trend: FindingTrend; feature: string }) {
  const { text, Icon, colorClass } = deltaDisplayOf(openDeltaOf(trend));

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
      <Card data-testid={`${feature}-card-trend-open`}>
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Offener Bestand
          </CardTitle>
        </CardHeader>
        <CardContent className="flex items-baseline gap-2">
          <p className="text-3xl font-semibold">{openNowOf(trend)}</p>
          <span
            className={`flex items-center gap-1 text-sm ${colorClass}`}
            data-testid={`${feature}-text-trend-open-delta`}
          >
            <Icon className="size-4" aria-hidden />
            {text}
          </span>
        </CardContent>
      </Card>
      <StatCard
        title="Unangetastet"
        value={trend.untouchedNow}
        testId={`${feature}-card-trend-untouched`}
      />
      <StatCard
        title="In Arbeit"
        value={trend.inProgressNow}
        testId={`${feature}-card-trend-in-progress`}
      />
      <StatCard
        title="Neu im Zeitraum"
        value={trend.newTotal}
        testId={`${feature}-card-trend-new`}
      />
      <StatCard
        title="Erledigt im Zeitraum"
        value={trend.closedTotal}
        testId={`${feature}-card-trend-closed`}
      />
    </div>
  );
}
