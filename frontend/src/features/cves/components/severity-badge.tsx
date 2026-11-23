import { SEVERITY_BADGE_VARIANT } from "@/shared/lib/severity";
import { Badge } from "@/shared/ui/badge";

import type { RiskLevel } from "../model/types";

export function SeverityBadge({ level, score }: { level: RiskLevel; score: number }) {
  return (
    <Badge variant={SEVERITY_BADGE_VARIANT[level]} data-testid="cves-badge-severity">
      {level} ({score})
    </Badge>
  );
}
