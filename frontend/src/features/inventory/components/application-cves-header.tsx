import type { ColumnFilterOption } from "@/shared/components/column-filter";
import { ColumnFilter } from "@/shared/components/column-filter";
import { TableHead, TableHeader, TableRow } from "@/shared/ui/table";

import {
  CVE_ECOSYSTEM_OPTIONS,
  CVE_SEVERITY_OPTIONS,
  CVE_STATUS_OPTIONS,
  type CveColumnOptions,
  type CveFilters,
} from "../model/cve-filters";

interface HeadProps {
  filters: CveFilters;
  onChange: (filters: CveFilters) => void;
}

interface ChoiceHeadProps extends HeadProps {
  label: string;
  field: "severities" | "statuses" | "ecosystems" | "advisoryIds" | "componentNames";
  options: ReadonlyArray<ColumnFilterOption<string>>;
  name: string;
  searchable?: boolean;
}

function ChoiceHead({
  filters,
  onChange,
  label,
  field,
  options,
  name,
  searchable,
}: ChoiceHeadProps) {
  return (
    <TableHead>
      <ColumnFilter
        label={label}
        options={options}
        selected={filters[field]}
        onChange={(values) => onChange({ ...filters, [field]: values })}
        searchable={searchable}
        feature="inventory"
        name={name}
      />
    </TableHead>
  );
}

interface ApplicationCvesHeaderProps extends HeadProps {
  options: CveColumnOptions;
}

/** Kopfzeile des CVE-Reiters; Überschriften sind die Filter (ohne Anwendung). */
export function ApplicationCvesHeader({ filters, onChange, options }: ApplicationCvesHeaderProps) {
  const head = { filters, onChange };
  return (
    <TableHeader>
      <TableRow>
        <ChoiceHead
          {...head}
          label="Risiko"
          field="severities"
          options={CVE_SEVERITY_OPTIONS}
          name="severity"
        />
        <ChoiceHead
          {...head}
          label="Advisory"
          field="advisoryIds"
          options={options.advisories}
          name="advisory"
          searchable
        />
        <ChoiceHead
          {...head}
          label="Komponente"
          field="componentNames"
          options={options.components}
          name="component"
          searchable
        />
        <ChoiceHead
          {...head}
          label="Ökosystem"
          field="ecosystems"
          options={CVE_ECOSYSTEM_OPTIONS}
          name="ecosystem"
        />
        <TableHead>Fix</TableHead>
        <ChoiceHead
          {...head}
          label="Status"
          field="statuses"
          options={CVE_STATUS_OPTIONS}
          name="status"
        />
      </TableRow>
    </TableHeader>
  );
}
