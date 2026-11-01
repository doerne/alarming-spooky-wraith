import { RotateCcw } from "lucide-react";

import { Button } from "@/shared/ui/button";

interface FilterSummaryProps {
  shown: number;
  total: number;
  onReset: () => void;
}

export function FilterSummary({ shown, total, onReset }: FilterSummaryProps) {
  if (shown === 0 && total > 0) {
    return (
      <div className="flex flex-wrap items-center gap-3" data-testid="cves-card-no-results">
        <p className="text-sm text-muted-foreground" data-testid="cves-text-no-results">
          Keine Funde für diese Filter.
        </p>
        <Button
          variant="outline"
          size="sm"
          onClick={onReset}
          data-testid="cves-btn-reset-no-results"
        >
          <RotateCcw aria-hidden />
          Filter zurücksetzen
        </Button>
      </div>
    );
  }
  return (
    <p className="text-sm text-muted-foreground" data-testid="cves-text-filter-summary">
      {shown} von {total} Funden
    </p>
  );
}
