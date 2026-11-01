import { RotateCcw } from "lucide-react";

import { MultiToggleFilter } from "@/shared/components/multi-toggle-filter";
import { SearchInput } from "@/shared/components/search-input";
import { Button } from "@/shared/ui/button";

import {
  ECOSYSTEM_OPTIONS,
  type FindingFilters,
  SEVERITY_OPTIONS,
  STATUS_OPTIONS,
  hasActiveFilters,
} from "../model/filters";

const SELECT_CLASS = "border-input bg-transparent h-8 rounded-md border px-2 text-sm shadow-xs";
const ALL_APPLICATIONS = "";

interface FindingsFilterBarProps {
  filters: FindingFilters;
  applications: ReadonlyArray<{ id: number; name: string }>;
  onChange: (filters: FindingFilters) => void;
  onReset: () => void;
}

function ApplicationFilter({
  filters,
  applications,
  onChange,
}: Omit<FindingsFilterBarProps, "onReset">) {
  if (applications.length === 0) return null;
  return (
    <label className="flex flex-col gap-1 text-xs text-muted-foreground">
      Anwendung
      <select
        className={SELECT_CLASS}
        value={filters.applicationId === null ? ALL_APPLICATIONS : String(filters.applicationId)}
        onChange={(event) =>
          onChange({
            ...filters,
            applicationId:
              event.target.value === ALL_APPLICATIONS ? null : Number(event.target.value),
          })
        }
        data-testid="cves-select-application"
      >
        <option value={ALL_APPLICATIONS}>Alle</option>
        {applications.map((application) => (
          <option key={application.id} value={application.id}>
            {application.name}
          </option>
        ))}
      </select>
    </label>
  );
}

/** Filterleiste der Funde-Tabelle (rein; Zustand hält die Seite). */
export function FindingsFilterBar({
  filters,
  applications,
  onChange,
  onReset,
}: FindingsFilterBarProps) {
  return (
    <div className="flex flex-col gap-3" data-testid="cves-form-filters">
      <div className="flex flex-wrap items-end gap-4">
        <MultiToggleFilter
          label="Schweregrad"
          options={SEVERITY_OPTIONS}
          selected={filters.severities}
          onChange={(severities) => onChange({ ...filters, severities })}
          testIdPrefix="cves-select-severity"
        />
        <MultiToggleFilter
          label="Status"
          options={STATUS_OPTIONS}
          selected={filters.statuses}
          onChange={(statuses) => onChange({ ...filters, statuses })}
          testIdPrefix="cves-select-status"
        />
      </div>
      <div className="flex flex-wrap items-end gap-4">
        <MultiToggleFilter
          label="Ökosystem"
          options={ECOSYSTEM_OPTIONS}
          selected={filters.ecosystems}
          onChange={(ecosystems) => onChange({ ...filters, ecosystems })}
          testIdPrefix="cves-select-ecosystem"
        />
        <ApplicationFilter filters={filters} applications={applications} onChange={onChange} />
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <div className="min-w-56 flex-1">
          <SearchInput
            value={filters.query}
            onChange={(query) => onChange({ ...filters, query })}
            placeholder="CVE-ID, Titel oder Komponente suchen"
            testId="cves-input-search"
          />
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={onReset}
          disabled={!hasActiveFilters(filters)}
          data-testid="cves-btn-reset-filters"
        >
          <RotateCcw aria-hidden />
          Filter zurücksetzen
        </Button>
      </div>
    </div>
  );
}
