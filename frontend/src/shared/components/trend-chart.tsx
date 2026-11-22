import { Bar, CartesianGrid, ComposedChart, Line, XAxis, YAxis } from "recharts";

import type { FindingTrend } from "@/shared/api/finding-trend";
import { hasMovement, weekLabelOf } from "@/shared/lib/trend";
import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/card";
import type { ChartConfig } from "@/shared/ui/chart";
import {
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
} from "@/shared/ui/chart";

const chartConfig = {
  new: { label: "Neu", color: "var(--chart-5)" },
  closed: { label: "Erledigt", color: "var(--chart-1)" },
  openAtEnd: { label: "Offener Bestand", color: "var(--foreground)" },
} satisfies ChartConfig;

export function TrendChart({ trend, feature }: { trend: FindingTrend; feature: string }) {
  const chartData = trend.weeks.map((week) => ({ ...week, label: weekLabelOf(week.weekStart) }));

  return (
    <Card data-testid={`${feature}-card-trend-chart`}>
      <CardHeader>
        <CardTitle>Verlauf</CardTitle>
      </CardHeader>
      <CardContent>
        {hasMovement(trend) ? (
          <ChartContainer
            config={chartConfig}
            className="h-[280px] w-full"
            data-testid={`${feature}-chart-trend`}
          >
            <ComposedChart accessibilityLayer data={chartData}>
              <CartesianGrid vertical={false} />
              <XAxis dataKey="label" tickLine={false} axisLine={false} tickMargin={8} />
              <YAxis allowDecimals={false} width={32} tickLine={false} axisLine={false} />
              <ChartTooltip content={<ChartTooltipContent />} />
              <ChartLegend content={<ChartLegendContent />} />
              <Bar dataKey="new" fill="var(--color-new)" radius={4} />
              <Bar dataKey="closed" fill="var(--color-closed)" radius={4} />
              <Line
                dataKey="openAtEnd"
                type="linear"
                stroke="var(--color-openAtEnd)"
                strokeWidth={2}
                dot={{ r: 3, fill: "var(--color-openAtEnd)" }}
              />
            </ComposedChart>
          </ChartContainer>
        ) : (
          <p className="text-sm text-muted-foreground" data-testid={`${feature}-text-trend-empty`}>
            Im Zeitraum keine neuen oder erledigten Funde.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
