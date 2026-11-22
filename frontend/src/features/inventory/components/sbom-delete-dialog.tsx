import { Button } from "@/shared/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/shared/ui/dialog";

import type { SbomSummary } from "../model/sbom-types";

interface SbomDeleteDialogProps {
  sbom: SbomSummary;
  isDeleting: boolean;
  error: string | null;
  onConfirm: (sbom: SbomSummary) => void;
  onCancel: () => void;
}

/** Bestätigung vor dem Löschen einer SBOM samt Versionen, Komponenten und Treffern. */
export function SbomDeleteDialog({
  sbom,
  isDeleting,
  error,
  onConfirm,
  onCancel,
}: SbomDeleteDialogProps) {
  const componentCount = sbom.current?.componentCount ?? 0;
  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) onCancel();
      }}
    >
      <DialogContent data-testid="inventory-dialog-sbom-delete">
        <DialogHeader>
          <DialogTitle>{sbom.name} löschen?</DialogTitle>
          <DialogDescription>
            Alle {sbom.versionCount} Versionen, {componentCount} Komponenten und deren Treffer
            werden entfernt. Das lässt sich nicht rückgängig machen.
          </DialogDescription>
        </DialogHeader>
        {error && (
          <p
            role="alert"
            className="text-sm text-destructive"
            data-testid="inventory-error-sbom-delete"
          >
            {error}
          </p>
        )}
        <DialogFooter>
          <Button
            variant="outline"
            onClick={onCancel}
            data-testid="inventory-btn-sbom-delete-cancel"
          >
            Abbrechen
          </Button>
          <Button
            variant="destructive"
            disabled={isDeleting}
            onClick={() => onConfirm(sbom)}
            data-testid="inventory-btn-sbom-delete-confirm"
          >
            Löschen
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
