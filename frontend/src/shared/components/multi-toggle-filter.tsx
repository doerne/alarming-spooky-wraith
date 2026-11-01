import { ToggleGroup, ToggleGroupItem } from "@/shared/ui/toggle-group";

export interface FilterOption<T extends string> {
  value: T;
  label: string;
}

interface MultiToggleFilterProps<T extends string> {
  label: string;
  options: ReadonlyArray<FilterOption<T>>;
  selected: T[];
  onChange: (values: T[]) => void;
  testIdPrefix: string;
}

/** Mehrfachauswahl als Umschalt-Knöpfe; keine Auswahl = kein Filter. */
export function MultiToggleFilter<T extends string>({
  label,
  options,
  selected,
  onChange,
  testIdPrefix,
}: MultiToggleFilterProps<T>) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs text-muted-foreground">{label}</span>
      <ToggleGroup
        type="multiple"
        variant="outline"
        size="sm"
        value={selected}
        onValueChange={(values) => onChange(values as T[])}
        aria-label={label}
        className="flex-wrap"
        data-testid={testIdPrefix}
      >
        {options.map((option) => (
          <ToggleGroupItem
            key={option.value}
            value={option.value}
            data-testid={`${testIdPrefix}-${option.value}`}
          >
            {option.label}
          </ToggleGroupItem>
        ))}
      </ToggleGroup>
    </div>
  );
}
