import { AlertTriangle, ListChecks, ShieldAlert, ShieldX } from "lucide-react";
import type { LucideIcon } from "lucide-react";

import { Card, CardDescription, CardHeader, CardTitle } from "@/shared/ui/card";

import type { CveKpis } from "../model/stats";

interface KpiTile {
  key: string;
  label: string;
  value: number;
  icon: LucideIcon;
  accent: boolean;
}

function buildTiles(kpis: CveKpis): KpiTile[] {
  return [
    { key: "total", label: "Funde gesamt", value: kpis.total, icon: ListChecks, accent: false },
    { key: "kritisch", label: "Kritisch", value: kpis.kritisch, icon: ShieldX, accent: true },
    { key: "hoch", label: "Hoch", value: kpis.hoch, icon: ShieldAlert, accent: false },
    { key: "offen", label: "Offen", value: kpis.offen, icon: AlertTriangle, accent: false },
  ];
}

export function SectionCards({ kpis }: { kpis: CveKpis }) {
  return (
    <div
      className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4"
      data-testid="cves-list-kpis"
    >
      {buildTiles(kpis).map((tile) => (
        <Card key={tile.key} data-testid={`cves-card-kpi-${tile.key}`}>
          <CardHeader>
            <CardDescription className="flex items-center gap-2">
              <tile.icon className="size-4" aria-hidden />
              {tile.label}
            </CardDescription>
            <CardTitle
              className={
                tile.accent ? "text-3xl text-destructive tabular-nums" : "text-3xl tabular-nums"
              }
            >
              {tile.value}
            </CardTitle>
          </CardHeader>
        </Card>
      ))}
    </div>
  );
}
