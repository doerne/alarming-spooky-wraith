import { ClickableRow } from "@/shared/components/clickable-row";
import { Badge } from "@/shared/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/ui/table";

import type { ApplicationFinding } from "../model/types";

const RISK_VARIANT: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  kritisch: "destructive",
  hoch: "default",
  mittel: "secondary",
  niedrig: "outline",
};

interface ApplicationCvesProps {
  findings: ApplicationFinding[];
  onSelect: (advisoryId: string) => void;
}

export function ApplicationCves({ findings, onSelect }: ApplicationCvesProps) {
  if (findings.length === 0) {
    return (
      <p className="text-sm text-muted-foreground" data-testid="inventory-text-no-cves">
        Keine Funde für diese Anwendung. Starte einen Scan auf der Schwachstellen-Seite.
      </p>
    );
  }

  return (
    <Table data-testid="inventory-list-cves">
      <TableHeader>
        <TableRow>
          <TableHead>Risiko</TableHead>
          <TableHead>Advisory</TableHead>
          <TableHead>Komponente</TableHead>
          <TableHead>Fix</TableHead>
          <TableHead>Status</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {findings.map((finding) => (
          <ClickableRow
            key={`${finding.advisoryId}-${finding.componentId}`}
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
            <TableCell>{finding.fixVersion ?? "-"}</TableCell>
            <TableCell>{finding.status}</TableCell>
          </ClickableRow>
        ))}
      </TableBody>
    </Table>
  );
}
