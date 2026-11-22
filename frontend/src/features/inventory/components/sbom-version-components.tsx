import { Badge } from "@/shared/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/ui/table";

import type { SbomVersionDetail } from "../model/sbom-types";

export function SbomVersionComponents({ version }: { version: SbomVersionDetail }) {
  return (
    <Table data-testid="inventory-list-sbom-components">
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead>Version</TableHead>
          <TableHead>Ökosystem</TableHead>
          <TableHead>purl</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {version.components.map((entry, index) => (
          <TableRow
            key={`${entry.purl ?? entry.name}@${entry.version}#${index}`}
            data-testid={`inventory-item-sbom-entry-${index}`}
          >
            <TableCell>{entry.name}</TableCell>
            <TableCell>{entry.version}</TableCell>
            <TableCell>
              {entry.ecosystem ?? "-"}
              {!entry.checked && (
                <Badge
                  variant="secondary"
                  className="ml-2"
                  data-testid={`inventory-text-sbom-unchecked-${index}`}
                >
                  nicht geprüft
                </Badge>
              )}
            </TableCell>
            <TableCell className="max-w-64 truncate text-muted-foreground" title={entry.purl ?? ""}>
              {entry.purl ?? "-"}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
