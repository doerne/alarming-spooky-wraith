import { RotateCcw } from "lucide-react";

import { Button } from "@/shared/ui/button";

interface FilterSummaryBarProps {
  shown: number;
  total: number;
  active: boolean;
  feature: string;
  onReset: () => void;
}

/** „N von M Funden“ + Zurücksetzen über einer gefilterten Tabelle. */
export function FilterSummaryBar({
  shown,
  total,
  active,
  feature,
  onReset,
}: FilterSummaryBarProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <p className="text-sm text-muted-foreground" data-testid={`${feature}-text-filter-summary`}>
        {shown} von {total} Funden
      </p>
      <Button
        variant="outline"
        size="sm"
        onClick={onReset}
        disabled={!active}
        data-testid={`${feature}-btn-reset-filters`}
      >
        <RotateCcw aria-hidden />
        Filter zurücksetzen
      </Button>
    </div>
  );
}
