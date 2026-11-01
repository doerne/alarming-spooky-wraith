import type { Source } from "../model/types";

function describe(source: Source): string {
  switch (source.lastStatus) {
    case "running":
      return "Läuft …";
    case "ok":
      return `${source.lastFindings ?? 0} Funde`;
    case "error":
      return `Fehler: ${source.lastMessage}`;
    case "skipped":
      return `Übersprungen: ${source.lastMessage}`;
    default:
      return "Noch nicht gelaufen";
  }
}

export function LastRun({ source }: { source: Source }) {
  const isError = source.lastStatus === "error";
  return (
    <span
      className={isError ? "text-sm text-destructive" : "text-sm text-muted-foreground"}
      data-testid={`sources-text-last-run-${source.key}`}
    >
      {describe(source)}
    </span>
  );
}
