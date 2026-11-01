import type { ColumnFilterOption } from "@/shared/components/column-filter";
import { ColumnFilter, ColumnSearch } from "@/shared/components/column-filter";
import { TableHead, TableHeader, TableRow } from "@/shared/ui/table";

import {
  type ApplicationOption,
  ECOSYSTEM_OPTIONS,
  type FindingFilters,
  SEVERITY_OPTIONS,
  STATUS_OPTIONS,
} from "../model/filters";

type ChoiceKey = "severities" | "statuses" | "ecosystems";
type QueryKey = "advisoryQuery" | "componentQuery";

interface HeadProps {
  filters: FindingFilters;
  onChange: (filters: FindingFilters) => void;
}

interface ChoiceHeadProps extends HeadProps {
  label: string;
  field: ChoiceKey;
  options: ReadonlyArray<ColumnFilterOption<string>>;
  name: string;
}

function ChoiceHead({ filters, onChange, label, field, options, name }: ChoiceHeadProps) {
  return (
    <TableHead>
      <ColumnFilter
        label={label}
        options={options}
        selected={filters[field]}
        onChange={(values) => onChange({ ...filters, [field]: values })}
        feature="cves"
        name={name}
      />
    </TableHead>
  );
}

interface SearchHeadProps extends HeadProps {
  label: string;
  field: QueryKey;
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

interface ApplicationHeadProps extends HeadProps {
  applications: ReadonlyArray<ApplicationOption>;
}

type CvesTableHeaderProps = ApplicationHeadProps;

function ApplicationHead({ filters, onChange, applications }: ApplicationHeadProps) {
  const options = applications.map((app) => ({ value: String(app.id), label: app.name }));
  return (
    <TableHead>
      <ColumnFilter
        label="Anwendung"
        options={options}
        selected={filters.applicationIds.map(String)}
        onChange={(ids) => onChange({ ...filters, applicationIds: ids.map(Number) })}
        searchable
        feature="cves"
        name="application"
      />
    </TableHead>
  );
}

/** Kopfzeile, deren Spaltenüberschriften zugleich die Filter sind. */
export function CvesTableHeader({ filters, onChange, applications }: CvesTableHeaderProps) {
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
        <SearchHead
          {...head}
          label="Advisory"
          field="advisoryQuery"
          testId="cves-input-filter-advisory"
        />
        <ApplicationHead {...head} applications={applications} />
        <SearchHead
          {...head}
          label="Komponente"
          field="componentQuery"
          testId="cves-input-filter-component"
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
