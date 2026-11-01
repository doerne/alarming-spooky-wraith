import { ClickableRow } from "@/shared/components/clickable-row";
import { NoResultsRow, TableMessageRow } from "@/shared/components/table-message-row";
import { Table, TableBody, TableCell } from "@/shared/ui/table";

import type { ColumnOptions, EmptyState, FindingFilters } from "../model/filters";
import type { Finding } from "../model/types";
import { CvesTableHeader } from "./cves-table-header";
import { SeverityBadge } from "./severity-badge";

const COLUMN_COUNT = 7;

interface CvesTableProps {
  findings: Finding[];
  filters: FindingFilters;
  options: ColumnOptions;
  emptyState: EmptyState;
  onFiltersChange: (filters: FindingFilters) => void;
  onReset: () => void;
  onSelect: (advisoryId: string) => void;
}

function FindingRow({ item, onSelect }: { item: Finding; onSelect: (advisoryId: string) => void }) {
  return (
    <ClickableRow
      label={`Details zu ${item.advisoryId}`}
      testId={`cves-item-${item.advisoryId}-${item.componentId}`}
      onActivate={() => onSelect(item.advisoryId)}
    >
      <TableCell>
        <SeverityBadge level={item.riskLevel} score={item.riskScore} />
      </TableCell>
      <TableCell>{item.cveId ?? item.advisoryId}</TableCell>
      <TableCell>{item.applicationName}</TableCell>
      <TableCell>
        {item.componentName} {item.componentVersion}
      </TableCell>
      <TableCell>{item.ecosystem ?? "-"}</TableCell>
      <TableCell>{item.fixVersion ?? "-"}</TableCell>
      <TableCell>{item.status}</TableCell>
    </ClickableRow>
  );
}

export function CvesTable({
  findings,
  filters,
  options,
  emptyState,
  onFiltersChange,
  onReset,
  onSelect,
}: CvesTableProps) {
  return (
    <Table data-testid="cves-list-findings">
      <CvesTableHeader filters={filters} options={options} onChange={onFiltersChange} />
      <TableBody>
        {emptyState === "no-results" ? (
          <NoResultsRow colSpan={COLUMN_COUNT} feature="cves" onReset={onReset} />
        ) : null}
        {emptyState === "no-findings" ? (
          <TableMessageRow colSpan={COLUMN_COUNT} testId="cves-text-no-findings">
            Noch keine Funde – starte einen Scan.
          </TableMessageRow>
        ) : null}
        {findings.map((item) => (
          <FindingRow
            key={`${item.advisoryId}-${item.componentId}`}
            item={item}
            onSelect={onSelect}
          />
        ))}
      </TableBody>
    </Table>
  );
}
