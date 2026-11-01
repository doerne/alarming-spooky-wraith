import { RotateCcw } from "lucide-react";

import { Button } from "@/shared/ui/button";

interface FilterSummaryProps {
  shown: number;
  total: number;
  active: boolean;
  onReset: () => void;
}

export function FilterSummary({ shown, total, active, onReset }: FilterSummaryProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <p className="text-sm text-muted-foreground" data-testid="cves-text-filter-summary">
        {shown} von {total} Funden
      </p>
      <Button
        variant="outline"
        size="sm"
        onClick={onReset}
        disabled={!active}
        data-testid="cves-btn-reset-filters"
      >
        <RotateCcw aria-hidden />
        Filter zurücksetzen
      </Button>
    </div>
  );
}
