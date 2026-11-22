import { TriangleAlert } from "lucide-react";

import { cn } from "@/shared/lib/utils";

interface ScanFreshnessProps {
  text: string;
  warning: boolean;
  testId: string;
}

/** Zeigt, wie aktuell die CVE-Daten sind; Warnungen mit Symbol hervorgehoben. */
export function ScanFreshness({ text, warning, testId }: ScanFreshnessProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 text-sm",
        warning ? "text-destructive" : "text-muted-foreground",
      )}
      data-testid={testId}
    >
      {warning ? <TriangleAlert className="size-4" aria-hidden /> : null}
      {text}
    </span>
  );
}
