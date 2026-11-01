import { ClickableRow } from "@/shared/components/clickable-row";
import { NoResultsRow } from "@/shared/components/table-message-row";
import { Badge } from "@/shared/ui/badge";
import { Table, TableBody, TableCell } from "@/shared/ui/table";

import type { CveColumnOptions, CveFilters } from "../model/cve-filters";
import type { ApplicationFinding } from "../model/types";
import { ApplicationCvesHeader } from "./application-cves-header";

const COLUMN_COUNT = 6;

const RISK_VARIANT: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  kritisch: "destructive",
  hoch: "default",
  mittel: "secondary",
  niedrig: "outline",
};

interface ApplicationCvesProps {
  findings: ApplicationFinding[];
  filters: CveFilters;
  options: CveColumnOptions;
  onFiltersChange: (filters: CveFilters) => void;
  onReset: () => void;
  onSelect: (advisoryId: string) => void;
}

function FindingRow({
  finding,
  onSelect,
}: {
  finding: ApplicationFinding;
  onSelect: (advisoryId: string) => void;
}) {
  return (
    <ClickableRow
      label={`Details zu ${finding.advisoryId}`}
      testId={`inventory-item-cve-${finding.advisoryId}-${finding.componentId}`}
      onActivate={() => onSelect(finding.advisoryId)}
    >
      <TableCell>
        <Badge
          variant={RISK_VARIANT[finding.riskLevel] ?? "outline"}
          data-testid="inventory-text-risk"
        >
          {finding.riskLevel} ({finding.riskScore})
        </Badge>
      </TableCell>
      <TableCell>{finding.cveId ?? finding.advisoryId}</TableCell>
      <TableCell>
        {finding.componentName} {finding.componentVersion}
      </TableCell>
      <TableCell>{finding.ecosystem ?? "-"}</TableCell>
      <TableCell>{finding.fixVersion ?? "-"}</TableCell>
      <TableCell>{finding.status}</TableCell>
    </ClickableRow>
  );
}

export function ApplicationCves({
  findings,
  filters,
  options,
  onFiltersChange,
  onReset,
  onSelect,
}: ApplicationCvesProps) {
  return (
    <Table data-testid="inventory-list-cves">
      <ApplicationCvesHeader filters={filters} options={options} onChange={onFiltersChange} />
      <TableBody>
        {findings.length === 0 ? (
          <NoResultsRow colSpan={COLUMN_COUNT} feature="inventory" onReset={onReset} />
        ) : null}
        {findings.map((finding) => (
          <FindingRow
            key={`${finding.advisoryId}-${finding.componentId}`}
            finding={finding}
            onSelect={onSelect}
          />
        ))}
      </TableBody>
    </Table>
  );
}
