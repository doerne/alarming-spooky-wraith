import type { SbomUploadResult } from "../model/sbom-types";

function counts(result: SbomUploadResult): string {
  const parts = [
    `${result.added} hinzugefügt`,
    `${result.removed} entfernt`,
    `${result.kept} unverändert`,
    `${result.unchecked} nicht geprüft`,
  ];
  if (result.skipped > 0) parts.push(`${result.skipped} übersprungen`);
  return parts.join(" · ");
}

export function SbomUploadResultText({ result }: { result: SbomUploadResult }) {
  return (
    <p
      className="text-sm text-muted-foreground"
      role="status"
      data-testid="inventory-text-sbom-result"
    >
      {counts(result)}. Neue Treffer erscheinen nach dem nächsten Scan.
    </p>
  );
}
