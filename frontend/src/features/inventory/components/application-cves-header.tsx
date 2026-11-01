import type { ColumnFilterOption } from "@/shared/components/column-filter";
import { ColumnFilter, ColumnSearch } from "@/shared/components/column-filter";
import { TableHead, TableHeader, TableRow } from "@/shared/ui/table";

import {
  CVE_ECOSYSTEM_OPTIONS,
  CVE_SEVERITY_OPTIONS,
  CVE_STATUS_OPTIONS,
  type CveFilters,
} from "../model/cve-filters";

interface HeadProps {
  filters: CveFilters;
  onChange: (filters: CveFilters) => void;
}

interface ChoiceHeadProps extends HeadProps {
  label: string;
  field: "severities" | "statuses" | "ecosystems";
  options: ReadonlyArray<ColumnFilterOption<string>>;
  testIdPrefix: string;
}

function ChoiceHead({ filters, onChange, label, field, options, testIdPrefix }: ChoiceHeadProps) {
  return (
    <TableHead>
      <ColumnFilter
        label={label}
        options={options}
        selected={filters[field]}
        onChange={(values) => onChange({ ...filters, [field]: values })}
        testIdPrefix={testIdPrefix}
      />
    </TableHead>
  );
}

interface SearchHeadProps extends HeadProps {
  label: string;
  field: "advisoryQuery" | "componentQuery";
  testId: string;
}

function SearchHead({ filters, onChange, label, field, testId }: SearchHeadProps) {
  return (
    <TableHead>
      <ColumnSearch
        label={label}
        value={filters[field]}
        onChange={(value) => onChange({ ...filters, [field]: value })}
        testId={testId}
      />
    </TableHead>
  );
}

/** Kopfzeile des CVE-Reiters; Überschriften sind die Filter (ohne Anwendung). */
export function ApplicationCvesHeader({ filters, onChange }: HeadProps) {
  const head = { filters, onChange };
  return (
    <TableHeader>
      <TableRow>
        <ChoiceHead
          {...head}
          label="Risiko"
          field="severities"
          options={CVE_SEVERITY_OPTIONS}
          testIdPrefix="inventory-select-severity"
        />
        <SearchHead
          {...head}
          label="Advisory"
          field="advisoryQuery"
          testId="inventory-input-filter-advisory"
        />
        <SearchHead
          {...head}
          label="Komponente"
          field="componentQuery"
          testId="inventory-input-filter-component"
        />
        <ChoiceHead
          {...head}
          label="Ökosystem"
          field="ecosystems"
          options={CVE_ECOSYSTEM_OPTIONS}
          testIdPrefix="inventory-select-ecosystem"
        />
        <TableHead>Fix</TableHead>
        <ChoiceHead
          {...head}
          label="Status"
          field="statuses"
          options={CVE_STATUS_OPTIONS}
          testIdPrefix="inventory-select-status"
        />
      </TableRow>
    </TableHeader>
  );
}
