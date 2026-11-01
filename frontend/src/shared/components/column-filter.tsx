import { Filter } from "lucide-react";
import { useState } from "react";

import { slug } from "@/shared/lib/slug";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";
import { Checkbox } from "@/shared/ui/checkbox";
import { Input } from "@/shared/ui/input";
import { Popover, PopoverContent, PopoverTrigger } from "@/shared/ui/popover";

export interface ColumnFilterOption<T extends string> {
  value: T;
  label: string;
}

interface ColumnFilterProps<T extends string> {
  label: string;
  options: ReadonlyArray<ColumnFilterOption<T>>;
  selected: T[];
  onChange: (values: T[]) => void;
  searchable?: boolean;
  testIdPrefix: string;
}

function toggle<T>(values: T[], value: T): T[] {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value];
}

interface OptionListProps<T extends string> {
  options: ReadonlyArray<ColumnFilterOption<T>>;
  selected: T[];
  onChange: (values: T[]) => void;
  testIdPrefix: string;
}

function OptionList<T extends string>({
  options,
  selected,
  onChange,
  testIdPrefix,
}: OptionListProps<T>) {
  if (options.length === 0) {
    return (
      <p className="px-1 py-2 text-sm text-muted-foreground" data-testid={`${testIdPrefix}-empty`}>
        Keine Treffer
      </p>
    );
  }
  return (
    <ul
      className="flex max-h-64 flex-col gap-1 overflow-y-auto"
      data-testid={`${testIdPrefix}-list`}
    >
      {options.map((option) => {
        const id = `${testIdPrefix}-${slug(option.value)}`;
        return (
          <li
            key={option.value}
            className="flex items-center gap-2 rounded-sm px-1 py-1 hover:bg-accent"
          >
            <Checkbox
              id={id}
              checked={selected.includes(option.value)}
              onCheckedChange={() => onChange(toggle(selected, option.value))}
              data-testid={`${testIdPrefix}-option-${slug(option.value)}`}
            />
            <label htmlFor={id} className="flex-1 cursor-pointer text-sm">
              {option.label}
            </label>
          </li>
        );
      })}
    </ul>
  );
}

/** Filter in einer Spaltenüberschrift: Auswahlliste mit Häkchen, optional durchsuchbar. */
export function ColumnFilter<T extends string>({
  label,
  options,
  selected,
  onChange,
  searchable = false,
  testIdPrefix,
}: ColumnFilterProps<T>) {
  const [search, setSearch] = useState("");
  const needle = search.trim().toLowerCase();
  const visible = options.filter((option) => option.label.toLowerCase().includes(needle));
  const active = selected.length > 0;

  return (
    <Popover onOpenChange={(open) => (open ? undefined : setSearch(""))}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className={cn("-ml-2 h-8 gap-1 font-medium", active && "text-primary")}
          aria-label={`${label} filtern`}
          data-testid={testIdPrefix}
        >
          {label}
          <Filter className={cn("size-3.5", !active && "text-muted-foreground")} aria-hidden />
          {active ? <span className="text-xs">{selected.length}</span> : null}
        </Button>
      </PopoverTrigger>
      <PopoverContent align="start" className="flex w-60 flex-col gap-2 p-2">
        {searchable ? (
          <Input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder={`${label} suchen`}
            aria-label={`${label} suchen`}
            className="h-8"
            data-testid={`${testIdPrefix}-search`}
          />
        ) : null}
        <OptionList
          options={visible}
          selected={selected}
          onChange={onChange}
          testIdPrefix={testIdPrefix}
        />
        <Button
          variant="ghost"
          size="sm"
          onClick={() => onChange([])}
          disabled={!active}
          data-testid={`${testIdPrefix}-clear`}
        >
          Auswahl löschen
        </Button>
      </PopoverContent>
    </Popover>
  );
}

interface ColumnSearchProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  testId: string;
}

/** Suchfeld in einer Spaltenüberschrift. */
export function ColumnSearch({ label, value, onChange, testId }: ColumnSearchProps) {
  return (
    <div className="flex flex-col gap-1 py-1">
      <span className={cn("font-medium", value && "text-primary")}>{label}</span>
      <Input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Filtern …"
        aria-label={`${label} filtern`}
        className="h-7 min-w-28 text-xs font-normal"
        data-testid={testId}
      />
    </div>
  );
}
