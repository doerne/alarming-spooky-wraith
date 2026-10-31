import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts";

import { Card, CardContent, CardHeader, CardTitle } from "@/shared/ui/card";
import type { ChartConfig } from "@/shared/ui/chart";
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/shared/ui/chart";

import type { RiskLevel } from "../model/types";
import type { SeverityCount } from "../model/stats";

// Sequentielle Einfaerbung: je schwerwiegender, desto dunkler.
const LEVEL_COLOR: Record<RiskLevel, string> = {
  kritisch: "var(--chart-5)",
  hoch: "var(--chart-4)",
  mittel: "var(--chart-3)",
  niedrig: "var(--chart-1)",
};

const chartConfig = {
  count: { label: "Funde" },
} satisfies ChartConfig;

export function SeverityChart({ data }: { data: SeverityCount[] }) {
  const chartData = data.map((entry) => ({
    label: entry.label,
    count: entry.count,
    fill: LEVEL_COLOR[entry.level],
  }));

  return (
    <Card data-testid="cves-card-severity-chart">
      <CardHeader>
        <CardTitle>Funde nach Schweregrad</CardTitle>
      </CardHeader>
      <CardContent>
        <ChartContainer config={chartConfig} className="h-[260px] w-full">
          <BarChart accessibilityLayer data={chartData}>
            <CartesianGrid vertical={false} />
            <XAxis dataKey="label" tickLine={false} axisLine={false} tickMargin={8} />
            <YAxis allowDecimals={false} width={32} tickLine={false} axisLine={false} />
            <ChartTooltip content={<ChartTooltipContent />} />
            <Bar dataKey="count" radius={4} />
          </BarChart>
        </ChartContainer>
      </CardContent>
    </Card>
  );
}
