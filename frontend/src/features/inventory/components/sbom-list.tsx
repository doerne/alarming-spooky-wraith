import { FilePlus2, History, Trash2 } from "lucide-react";

import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";

import type { SbomSummary } from "../model/sbom-types";
import { formatUploadedAt } from "./sbom-format";

export interface SbomListProps {
  sboms: SbomSummary[];
  onUploadVersion: (sbom: SbomSummary) => void;
  onShowHistory: (sbom: SbomSummary) => void;
  onDelete: (sbom: SbomSummary) => void;
}

function CurrentVersion({ sbom }: { sbom: SbomSummary }) {
  const current = sbom.current;
  if (current === null) {
    return <span className="text-sm text-muted-foreground">Keine aktuelle Version</span>;
  }
  return (
    <span className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
      <span className="font-medium text-foreground">{current.label}</span>
      <span>{formatUploadedAt(current.uploadedAt)}</span>
      <span>{current.componentCount} Komponenten</span>
      {current.uncheckedCount > 0 && (
        <Badge variant="secondary">{current.uncheckedCount} nicht geprüft</Badge>
      )}
      <span>{sbom.versionCount} Versionen</span>
    </span>
  );
}

export function SbomList({ sboms, onUploadVersion, onShowHistory, onDelete }: SbomListProps) {
  if (sboms.length === 0) {
    return (
      <p className="text-sm text-muted-foreground" data-testid="inventory-text-no-sboms">
        Noch keine SBOM hinterlegt.
      </p>
    );
  }

  return (
    <ul
      className="flex flex-col divide-y divide-border rounded-md border"
      data-testid="inventory-list-sboms"
    >
      {sboms.map((sbom) => (
        <li
          key={sbom.id}
          className="flex flex-wrap items-center justify-between gap-3 p-3"
          data-testid={`inventory-item-sbom-${sbom.id}`}
        >
          <div className="flex flex-col gap-1">
            <span className="font-medium">{sbom.name}</span>
            <CurrentVersion sbom={sbom} />
          </div>
          <div className="flex gap-1">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onUploadVersion(sbom)}
              aria-label={`Neue Version von ${sbom.name}`}
              data-testid={`inventory-btn-sbom-new-version-${sbom.id}`}
            >
              <FilePlus2 /> Neue Version
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onShowHistory(sbom)}
              aria-label={`Verlauf von ${sbom.name}`}
              data-testid={`inventory-btn-sbom-history-${sbom.id}`}
            >
              <History /> Verlauf
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => onDelete(sbom)}
              aria-label={`${sbom.name} löschen`}
              data-testid={`inventory-btn-sbom-delete-${sbom.id}`}
            >
              <Trash2 />
            </Button>
          </div>
        </li>
      ))}
    </ul>
  );
}
