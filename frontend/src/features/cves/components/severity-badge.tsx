import { Badge } from "@/shared/ui/badge";

import type { RiskLevel } from "../model/types";

const VARIANT: Record<RiskLevel, "default" | "secondary" | "destructive" | "outline"> = {
  kritisch: "destructive",
  hoch: "default",
  mittel: "secondary",
  niedrig: "outline",
};

export function SeverityBadge({ level, score }: { level: RiskLevel; score: number }) {
  return (
    <Badge variant={VARIANT[level]} data-testid="cves-badge-severity">
      {level} ({score})
    </Badge>
  );
}
