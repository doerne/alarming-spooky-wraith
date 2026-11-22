import { ArrowDown, ArrowUp } from "lucide-react";

import { ClickableRow } from "@/shared/components/clickable-row";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/shared/ui/table";

import type { ApplicationOverview, OverviewSort, SortKey } from "../model/overview";
import { OpenCell, SbomCell, ScanCell } from "./overview-cells";

const COLUMNS: ReadonlyArray<{ key: SortKey; label: string }> = [
  { key: "name", label: "Anwendung" },
  { key: "open", label: "Offen" },
  { key: "overdue", label: "Überfällig" },
  { key: "components", label: "Komponenten" },
  { key: "sbom", label: "SBOM" },
  { key: "scan", label: "Gescannt" },
  { key: "github", label: "GitHub" },
];

interface OverviewTableProps {
  rows: ApplicationOverview[];
  sort: OverviewSort;
  now: Date;
  onSort: (key: SortKey) => void;
  onSelect: (applicationId: number) => void;
}

interface SortHeadProps {
  column: { key: SortKey; label: string };
  sort: OverviewSort;
  onSort: (key: SortKey) => void;
}

function ariaSortOf(active: boolean, sort: OverviewSort): "ascending" | "descending" | "none" {
  if (!active) return "none";
  return sort.direction === "asc" ? "ascending" : "descending";
}

function SortHead({ column, sort, onSort }: SortHeadProps) {
  const active = sort.key === column.key;
  const ascending = sort.direction === "asc";
  const Arrow = ascending ? ArrowUp : ArrowDown;
  return (
    <TableHead aria-sort={ariaSortOf(active, sort)}>
      <Button
        variant="ghost"
        size="sm"
        className="-ml-2"
        onClick={() => onSort(column.key)}
        data-testid={`inventory-btn-sort-${column.key}`}
      >
        {column.label}
        {active ? <Arrow className="size-3" aria-hidden /> : null}
      </Button>
    </TableHead>
  );
}

function OverviewRow({
  row,
  now,
  onSelect,
}: Omit<OverviewTableProps, "rows" | "sort" | "onSort"> & { row: ApplicationOverview }) {
  return (
    <ClickableRow
      label={`${row.name} öffnen`}
      testId={`inventory-item-app-${row.id}`}
      onActivate={() => onSelect(row.id)}
    >
      <TableCell>
        <div className="font-medium">{row.name}</div>
        {row.description ? (
          <div className="max-w-64 truncate text-sm text-muted-foreground">{row.description}</div>
        ) : null}
      </TableCell>
      <TableCell>
        <OpenCell row={row} />
      </TableCell>
      <TableCell className={cn(row.overdue > 0 && "text-destructive")}>{row.overdue}</TableCell>
      <TableCell>{row.componentCount}</TableCell>
      <TableCell>
        <SbomCell row={row} now={now} />
      </TableCell>
      <TableCell>
        <ScanCell row={row} />
      </TableCell>
      <TableCell>{row.githubRepository ?? "–"}</TableCell>
    </ClickableRow>
  );
}

/** Eine Zeile je Anwendung; jeder Spaltenkopf sortiert, ein Klick auf die Zeile öffnet sie. */
export function OverviewTable({ rows, sort, now, onSort, onSelect }: OverviewTableProps) {
  return (
    <Table aria-label="Anwendungen" data-testid="inventory-list-overview">
      <TableHeader>
        <TableRow>
          {COLUMNS.map((column) => (
            <SortHead key={column.key} column={column} sort={sort} onSort={onSort} />
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row) => (
          <OverviewRow key={row.id} row={row} now={now} onSelect={onSelect} />
        ))}
      </TableBody>
    </Table>
  );
}
