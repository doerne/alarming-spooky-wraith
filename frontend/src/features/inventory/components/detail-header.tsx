import { ArrowLeft, Trash2 } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "@/shared/ui/button";

interface DetailHeaderProps {
  name: string;
  onBack: () => void;
  actions: ReactNode;
  /** `null`, solange die Anwendung noch nicht geladen ist. */
  onDelete: (() => void) | null;
}

/** Kopf der Anwendungsdetails: Zurück, Name, Aktionen (z. B. GitHub-Einstellungen) und Löschen. */
export function DetailHeader({ name, onBack, actions, onDelete }: DetailHeaderProps) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <Button
        variant="ghost"
        size="icon"
        onClick={onBack}
        aria-label="Zurück zur Übersicht"
        data-testid="inventory-btn-back"
      >
        <ArrowLeft />
      </Button>
      <h2 className="text-lg font-semibold" data-testid="inventory-text-app-name">
        {name}
      </h2>
      {actions}
      <Button
        variant="destructive"
        size="sm"
        onClick={onDelete ?? undefined}
        disabled={onDelete === null}
        data-testid="inventory-btn-delete-app"
      >
        <Trash2 /> Anwendung löschen
      </Button>
    </div>
  );
}
