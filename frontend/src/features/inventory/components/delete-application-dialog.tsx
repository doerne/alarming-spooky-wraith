import { Button } from "@/shared/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/shared/ui/dialog";

export interface ApplicationDataCounts {
  components: number;
  sboms: number;
  findings: number;
}

interface DeleteApplicationDialogProps {
  name: string;
  counts: ApplicationDataCounts;
  isDeleting: boolean;
  error: string | null;
  onConfirm: () => void;
  onCancel: () => void;
}

/** Bestätigung vor dem endgültigen Löschen einer Anwendung samt Komponenten, SBOMs und Funden. */
export function DeleteApplicationDialog({
  name,
  counts,
  isDeleting,
  error,
  onConfirm,
  onCancel,
}: DeleteApplicationDialogProps) {
  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) onCancel();
      }}
    >
      <DialogContent data-testid="inventory-dialog-delete-app">
        <DialogHeader>
          <DialogTitle>{name} löschen?</DialogTitle>
          <DialogDescription>
            {name} mit {counts.components} Komponenten, {counts.sboms} SBOMs und {counts.findings}{" "}
            Funden endgültig löschen? Bereits angelegte GitHub-Issues bleiben auf GitHub bestehen.
          </DialogDescription>
        </DialogHeader>
        {error && (
          <p
            role="alert"
            className="text-sm text-destructive"
            data-testid="inventory-error-delete-app"
          >
            {error}
          </p>
        )}
        <DialogFooter>
          <Button
            variant="outline"
            onClick={onCancel}
            data-testid="inventory-btn-cancel-delete-app"
          >
            Abbrechen
          </Button>
          <Button
            variant="destructive"
            disabled={isDeleting}
            onClick={onConfirm}
            data-testid="inventory-btn-confirm-delete-app"
          >
            Endgültig löschen
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
