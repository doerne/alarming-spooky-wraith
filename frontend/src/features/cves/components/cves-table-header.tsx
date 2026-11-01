import type { ColumnFilterOption } from "@/shared/components/column-filter";
import { ColumnFilter } from "@/shared/components/column-filter";
import { TableHead, TableHeader, TableRow } from "@/shared/ui/table";

import {
  type ColumnOptions,
  ECOSYSTEM_OPTIONS,
  type FindingFilters,
  SEVERITY_OPTIONS,
  STATUS_OPTIONS,
} from "../model/filters";

type ChoiceKey = "severities" | "statuses" | "ecosystems" | "advisoryIds" | "componentNames";

interface HeadProps {
  filters: FindingFilters;
  onChange: (filters: FindingFilters) => void;
}

interface ChoiceHeadProps extends HeadProps {
  label: string;
  field: ChoiceKey;
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
        feature="cves"
        name={name}
      />
    </TableHead>
  );
}

function ApplicationHead({ filters, onChange, options }: HeadProps & { options: ColumnOptions }) {
  return (
    <TableHead>
      <ColumnFilter
        label="Anwendung"
        options={options.applications}
        selected={filters.applicationIds.map(String)}
        onChange={(ids) => onChange({ ...filters, applicationIds: ids.map(Number) })}
        searchable
        feature="cves"
        name="application"
      />
    </TableHead>
  );
}

interface CvesTableHeaderProps extends HeadProps {
  options: ColumnOptions;
}

/** Kopfzeile, deren Spaltenüberschriften zugleich die Filter sind. */
export function CvesTableHeader({ filters, onChange, options }: CvesTableHeaderProps) {
  const head = { filters, onChange };
  return (
    <TableHeader>
      <TableRow>
        <ChoiceHead
          {...head}
          label="Risiko"
          field="severities"
          options={SEVERITY_OPTIONS}
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
        <ApplicationHead {...head} options={options} />
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
          options={ECOSYSTEM_OPTIONS}
          name="ecosystem"
        />
        <TableHead>Fix</TableHead>
        <ChoiceHead
          {...head}
          label="Status"
          field="statuses"
          options={STATUS_OPTIONS}
          name="status"
        />
      </TableRow>
    </TableHeader>
  );
}
