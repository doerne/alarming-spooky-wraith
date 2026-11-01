import { RotateCcw } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "@/shared/ui/button";
import { TableCell, TableRow } from "@/shared/ui/table";

interface TableMessageRowProps {
  colSpan: number;
  testId: string;
  children: ReactNode;
}

/** Meldung über die volle Tabellenbreite (z. B. „Noch keine Funde“). */
export function TableMessageRow({ colSpan, testId, children }: TableMessageRowProps) {
  return (
    <TableRow>
      <TableCell colSpan={colSpan} className="py-6 text-center">
        <span className="text-muted-foreground" data-testid={testId}>
          {children}
        </span>
      </TableCell>
    </TableRow>
  );
}

interface NoResultsRowProps {
  colSpan: number;
  feature: string;
  onReset: () => void;
}

/** Filter ohne Treffer: Hinweis + Zurücksetzen, die Tabelle (mit Kopf-Filtern) bleibt. */
export function NoResultsRow({ colSpan, feature, onReset }: NoResultsRowProps) {
  return (
    <TableRow>
      <TableCell colSpan={colSpan} className="py-6 text-center">
        <div className="flex flex-wrap items-center justify-center gap-3">
          <span className="text-muted-foreground" data-testid={`${feature}-text-no-results`}>
            Keine Funde für diese Filter.
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={onReset}
            data-testid={`${feature}-btn-reset-no-results`}
          >
            <RotateCcw aria-hidden />
            Filter zurücksetzen
          </Button>
        </div>
      </TableCell>
    </TableRow>
  );
}
