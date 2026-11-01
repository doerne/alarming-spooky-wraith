import { RotateCcw } from "lucide-react";

import { ClickableRow } from "@/shared/components/clickable-row";
import { Button } from "@/shared/ui/button";
import { Table, TableBody, TableCell, TableRow } from "@/shared/ui/table";

import type { FindingFilters } from "../model/filters";
import type { Finding } from "../model/types";
import { CvesTableHeader } from "./cves-table-header";
import { SeverityBadge } from "./severity-badge";

const COLUMN_COUNT = 7;

interface CvesTableProps {
  findings: Finding[];
  filters: FindingFilters;
  applications: ReadonlyArray<{ id: number; name: string }>;
  onFiltersChange: (filters: FindingFilters) => void;
  onReset: () => void;
  onSelect: (advisoryId: string) => void;
}

function NoResultsRow({ onReset }: { onReset: () => void }) {
  return (
    <TableRow>
      <TableCell colSpan={COLUMN_COUNT} className="py-6 text-center">
        <div className="flex flex-wrap items-center justify-center gap-3">
          <span className="text-muted-foreground" data-testid="cves-text-no-results">
            Keine Funde für diese Filter.
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={onReset}
            data-testid="cves-btn-reset-no-results"
          >
            <RotateCcw aria-hidden />
            Filter zurücksetzen
          </Button>
        </div>
      </TableCell>
    </TableRow>
  );
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
  applications,
  onFiltersChange,
  onReset,
  onSelect,
}: CvesTableProps) {
  return (
    <Table data-testid="cves-list-findings">
      <CvesTableHeader filters={filters} applications={applications} onChange={onFiltersChange} />
      <TableBody>
        {findings.length === 0 ? <NoResultsRow onReset={onReset} /> : null}
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
