import type { KeyboardEvent, ReactNode } from "react";

import { TableRow } from "@/shared/ui/table";

interface ClickableRowProps {
  label: string;
  testId: string;
  onActivate: () => void;
  children: ReactNode;
}

const ACTIVATION_KEYS = new Set(["Enter", " "]);

/** Tabellenzeile, die per Klick, Enter oder Leertaste eine Aktion auslöst. */
export function ClickableRow({ label, testId, onActivate, children }: ClickableRowProps) {
  const handleKey = (event: KeyboardEvent<HTMLTableRowElement>) => {
    if (!ACTIVATION_KEYS.has(event.key)) return;
    event.preventDefault();
    onActivate();
  };
  return (
    <TableRow
      tabIndex={0}
      aria-label={label}
      className="cursor-pointer focus-visible:outline-2 focus-visible:outline-ring"
      onClick={onActivate}
      onKeyDown={handleKey}
      data-testid={testId}
    >
      {children}
    </TableRow>
  );
}
