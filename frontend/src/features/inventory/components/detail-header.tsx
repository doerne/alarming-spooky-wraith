import { ArrowLeft } from "lucide-react";
import type { ReactNode } from "react";

import { Button } from "@/shared/ui/button";

interface DetailHeaderProps {
  name: string;
  onBack: () => void;
  actions: ReactNode;
}

/** Kopf der Anwendungsdetails: Zurück, Name und Aktionen (z. B. GitHub-Einstellungen). */
export function DetailHeader({ name, onBack, actions }: DetailHeaderProps) {
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
    </div>
  );
}
