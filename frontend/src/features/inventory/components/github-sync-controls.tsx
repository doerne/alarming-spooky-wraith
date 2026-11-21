import { Github } from "lucide-react";

import { Button } from "@/shared/ui/button";

interface GithubSyncControlsProps {
  hint: string | null;
  lastSyncedAt: string | null;
  lastSyncMessage: string;
  error: string | null;
  onOpenCreate: () => void;
  onSync: () => void;
}

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString("de-DE");
}

/** Buttons und Statuszeile der GitHub-Anbindung im CVE-Reiter (rein, ohne Daten). */
export function GithubSyncControls({
  hint,
  lastSyncedAt,
  lastSyncMessage,
  error,
  onOpenCreate,
  onSync,
}: GithubSyncControlsProps) {
  const disabled = hint !== null;
  return (
    <div className="flex flex-col gap-2" data-testid="inventory-card-github-sync">
      <div className="flex flex-wrap items-center justify-end gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={onSync}
          disabled={disabled}
          data-testid="inventory-btn-github-sync"
        >
          <Github /> Mit GitHub abgleichen
        </Button>
        <Button
          size="sm"
          onClick={onOpenCreate}
          disabled={disabled}
          data-testid="inventory-btn-github-create"
        >
          Issues in GitHub anlegen
        </Button>
      </div>
      {hint && (
        <p
          className="text-right text-sm text-muted-foreground"
          data-testid="inventory-text-github-hint"
        >
          {hint}
        </p>
      )}
      {error && (
        <p
          role="alert"
          className="text-right text-sm text-destructive"
          data-testid="inventory-error-github-sync"
        >
          {error}
        </p>
      )}
      <p
        className="text-right text-sm text-muted-foreground"
        data-testid="inventory-text-github-sync-status"
      >
        {lastSyncedAt
          ? `Letzter Abgleich: ${formatTime(lastSyncedAt)} · ${lastSyncMessage}`
          : "Noch kein Abgleich mit GitHub."}
      </p>
    </div>
  );
}
