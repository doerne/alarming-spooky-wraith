import { Badge } from "@/shared/ui/badge";

import type { SourceStatus } from "../model/types";

const LABEL: Record<SourceStatus, string> = {
  ready: "Bereit",
  missing_key: "Key fehlt",
  disabled: "Deaktiviert",
};

const VARIANT: Record<SourceStatus, "default" | "secondary" | "destructive" | "outline"> = {
  ready: "default",
  missing_key: "destructive",
  disabled: "outline",
};

export function SourceStatusBadge({
  sourceKey,
  status,
}: {
  sourceKey: string;
  status: SourceStatus;
}) {
  return (
    <Badge variant={VARIANT[status]} data-testid={`sources-text-status-${sourceKey}`}>
      {LABEL[status]}
    </Badge>
  );
}
