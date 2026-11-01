import { RotateCcw } from "lucide-react";

import { ClickableRow } from "@/shared/components/clickable-row";
import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import { Table, TableBody, TableCell, TableRow } from "@/shared/ui/table";

import type { CveFilters } from "../model/cve-filters";
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
  onFiltersChange: (filters: CveFilters) => void;
  onReset: () => void;
  onSelect: (advisoryId: string) => void;
}

function NoResultsRow({ onReset }: { onReset: () => void }) {
  return (
    <TableRow>
      <TableCell colSpan={COLUMN_COUNT} className="py-6 text-center">
        <div className="flex flex-wrap items-center justify-center gap-3">
          <span className="text-muted-foreground" data-testid="inventory-text-no-results">
            Keine Funde für diese Filter.
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={onReset}
            data-testid="inventory-btn-reset-no-results"
          >
            <RotateCcw aria-hidden />
            Filter zurücksetzen
          </Button>
        </div>
      </TableCell>
    </TableRow>
  );
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
  onFiltersChange,
  onReset,
  onSelect,
}: ApplicationCvesProps) {
  return (
    <Table data-testid="inventory-list-cves">
      <ApplicationCvesHeader filters={filters} onChange={onFiltersChange} />
      <TableBody>
        {findings.length === 0 ? <NoResultsRow onReset={onReset} /> : null}
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
