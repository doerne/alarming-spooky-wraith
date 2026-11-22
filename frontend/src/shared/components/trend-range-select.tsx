import { TREND_WEEK_OPTIONS, type TrendWeeks } from "@/shared/api/finding-trend";
import { ToggleGroup, ToggleGroupItem } from "@/shared/ui/toggle-group";

interface TrendRangeSelectProps {
  value: TrendWeeks;
  onChange: (weeks: TrendWeeks) => void;
  feature: string;
}

/** Zeitraum-Auswahl (4/12/26/52 Wochen) für den Finding-Trend. */
export function TrendRangeSelect({ value, onChange, feature }: TrendRangeSelectProps) {
  // Radix liefert beim erneuten Klick auf die aktive Auswahl einen leeren String.
  const handleChange = (selected: string) => {
    if (selected !== "") {
      onChange(Number(selected) as TrendWeeks);
    }
  };

  return (
    <ToggleGroup
      type="single"
      variant="outline"
      value={String(value)}
      onValueChange={handleChange}
      aria-label="Zeitraum"
      data-testid={`${feature}-select-trend-range`}
    >
      {TREND_WEEK_OPTIONS.map((weeks) => (
        <ToggleGroupItem
          key={weeks}
          value={String(weeks)}
          data-testid={`${feature}-btn-trend-range-${weeks}`}
        >
          {weeks} Wochen
        </ToggleGroupItem>
      ))}
    </ToggleGroup>
  );
}
