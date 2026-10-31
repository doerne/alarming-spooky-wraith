import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/ui/table";

import type { Finding } from "../model/types";
import { SeverityBadge } from "./severity-badge";

export function CvesTable({ findings }: { findings: Finding[] }) {
  return (
    <Table data-testid="cves-list-findings">
      <TableHeader>
        <TableRow>
          <TableHead>Risiko</TableHead>
          <TableHead>Advisory</TableHead>
          <TableHead>Anwendung</TableHead>
          <TableHead>Komponente</TableHead>
          <TableHead>Fix</TableHead>
          <TableHead>Status</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {findings.map((item) => (
          <TableRow key={item.advisoryId} data-testid={`cves-item-${item.advisoryId}`}>
            <TableCell>
              <SeverityBadge level={item.riskLevel} score={item.riskScore} />
            </TableCell>
            <TableCell>{item.cveId ?? item.advisoryId}</TableCell>
            <TableCell>{item.applicationName}</TableCell>
            <TableCell>
              {item.componentName} {item.componentVersion}
            </TableCell>
            <TableCell>{item.fixVersion ?? "-"}</TableCell>
            <TableCell>{item.status}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
