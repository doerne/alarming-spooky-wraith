import { FileDown } from "lucide-react";

import { Button } from "@/shared/ui/button";

import { applicationIssueExportPath } from "../api/inventory-api";

/** Download der offenen CVEs als Markdown-Vorlagen für GitHub-Issues (für KI-Agenten). */
export function CvesExportButton({ applicationId }: { applicationId: number }) {
  return (
    <Button asChild variant="outline" size="sm" data-testid="inventory-btn-cves-export">
      <a
        href={applicationIssueExportPath(applicationId)}
        download
        title="Offene CVEs als Markdown für GitHub-Issues"
        data-testid="inventory-link-cves-export"
      >
        <FileDown /> Für KI exportieren
      </a>
    </Button>
  );
}
