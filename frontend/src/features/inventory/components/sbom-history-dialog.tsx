import { Badge } from "@/shared/ui/badge";
import { Button } from "@/shared/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/shared/ui/dialog";

import type { SbomSummary, SbomVersionDetail, SbomVersionSummary } from "../model/sbom-types";
import { formatUploadedAt } from "./sbom-format";
import { SbomVersionComponents } from "./sbom-version-components";

interface SbomHistoryDialogProps {
  sbom: SbomSummary;
  versions: SbomVersionSummary[];
  selected: SbomVersionDetail | null;
  onSelect: (versionId: number) => void;
  onOpenChange: (open: boolean) => void;
}

interface VersionRowProps {
  version: SbomVersionSummary;
  isSelected: boolean;
  onSelect: (id: number) => void;
}

function VersionRow({ version, isSelected, onSelect }: VersionRowProps) {
  return (
    <li
      className="flex items-center justify-between gap-3 py-2"
      data-testid={`inventory-item-sbom-version-${version.id}`}
    >
      <span className="flex flex-wrap items-center gap-2 text-sm">
        <span className="font-medium">{version.label}</span>
        <span className="text-muted-foreground">{formatUploadedAt(version.uploadedAt)}</span>
        <span className="text-muted-foreground">{version.componentCount} Komponenten</span>
        <Badge variant={version.isCurrent ? "default" : "outline"}>
          {version.isCurrent ? "aktuell" : "archiviert"}
        </Badge>
      </span>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => onSelect(version.id)}
        aria-current={isSelected}
        aria-label={`Komponenten von ${version.label} anzeigen`}
        data-testid={`inventory-btn-sbom-version-${version.id}`}
      >
        Komponenten
      </Button>
    </li>
  );
}

/** Versionsverlauf einer SBOM; die gewählte Version zeigt ihre Komponentenliste. */
export function SbomHistoryDialog({
  sbom,
  versions,
  selected,
  onSelect,
  onOpenChange,
}: SbomHistoryDialogProps) {
  return (
    <Dialog open onOpenChange={onOpenChange}>
      <DialogContent
        className="max-h-[85vh] overflow-y-auto sm:max-w-3xl"
        data-testid="inventory-dialog-sbom-history"
      >
        <DialogHeader>
          <DialogTitle>Verlauf von {sbom.name}</DialogTitle>
          <DialogDescription>Archivierte Versionen werden nicht mehr geprüft.</DialogDescription>
        </DialogHeader>
        <ul className="divide-y divide-border" data-testid="inventory-list-sbom-versions">
          {versions.map((version) => (
            <VersionRow
              key={version.id}
              version={version}
              isSelected={version.id === selected?.id}
              onSelect={onSelect}
            />
          ))}
        </ul>
        {selected && (
          <section className="flex flex-col gap-2" data-testid="inventory-card-sbom-version">
            <h3 className="text-sm font-medium">Komponenten von {selected.label}</h3>
            <SbomVersionComponents version={selected} />
          </section>
        )}
      </DialogContent>
    </Dialog>
  );
}
