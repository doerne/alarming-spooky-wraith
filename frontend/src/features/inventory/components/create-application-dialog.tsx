import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/shared/ui/dialog";

import type { ApplicationInput } from "../model/schema";
import { ApplicationForm } from "./application-form";

interface CreateApplicationDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreate: (values: ApplicationInput) => void;
  isCreating: boolean;
  error: string | null;
}

export function CreateApplicationDialog({
  open,
  onOpenChange,
  onCreate,
  isCreating,
  error,
}: CreateApplicationDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="inventory-dialog-create-app">
        <DialogHeader>
          <DialogTitle>Anwendung anlegen</DialogTitle>
          <DialogDescription>Danach öffnet sich die neue Anwendung.</DialogDescription>
        </DialogHeader>
        <ApplicationForm onCreate={onCreate} isSubmitting={isCreating} />
        {error ? (
          <p
            role="alert"
            className="text-sm text-destructive"
            data-testid="inventory-error-create-app"
          >
            {error}
          </p>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
