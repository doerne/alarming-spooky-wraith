export interface GitHubSyncAvailability {
  repository: string | null;
  configured: boolean;
  running: boolean;
}

/** Erklärt, warum die GitHub-Buttons deaktiviert sind; ``null``, wenn sie gehen. */
export function githubSyncHint({
  repository,
  configured,
  running,
}: GitHubSyncAvailability): string | null {
  if (!configured) return "GitHub ist auf dem Server nicht konfiguriert.";
  if (!repository) return "Hinterlege zuerst ein Repository (GitHub-Einstellungen).";
  if (running) return "Ein Scan oder Abgleich läuft gerade.";
  return null;
}
