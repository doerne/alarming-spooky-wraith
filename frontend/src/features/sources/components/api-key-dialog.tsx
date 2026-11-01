import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";

import { Button } from "@/shared/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/shared/ui/dialog";
import { Field, FieldDescription, FieldError, FieldLabel } from "@/shared/ui/field";
import { Input } from "@/shared/ui/input";

import { type ApiKeyForm, type Source, apiKeyFormSchema } from "../model/types";

interface ApiKeyDialogProps {
  source: Source | null;
  error?: string | null;
  onSave: (apiKey: string) => void;
  onRemove: () => void;
  onClose: () => void;
}

function ApiKeyFormBody({
  source,
  onSave,
  onRemove,
}: Omit<ApiKeyDialogProps, "onClose"> & { source: Source }) {
  const form = useForm<ApiKeyForm>({
    resolver: zodResolver(apiKeyFormSchema),
    defaultValues: { apiKey: "" },
  });
  const error = form.formState.errors.apiKey;
  const submit = form.handleSubmit(({ apiKey }) => onSave(apiKey));

  return (
    <form
      onSubmit={submit}
      noValidate
      className="flex flex-col gap-4"
      data-testid="sources-form-api-key"
    >
      <Field data-invalid={Boolean(error)}>
        <FieldLabel htmlFor="sources-api-key">API-Key</FieldLabel>
        <Input
          id="sources-api-key"
          type="password"
          autoComplete="off"
          aria-invalid={Boolean(error)}
          data-testid="sources-input-api-key"
          {...form.register("apiKey")}
        />
        {source.apiKeyHint ? <FieldDescription>{source.apiKeyHint}</FieldDescription> : null}
        <FieldError errors={[error]} data-testid="sources-error-api-key" />
      </Field>
      <DialogFooter>
        {source.hasApiKey ? (
          <Button
            type="button"
            variant="destructive"
            onClick={onRemove}
            data-testid="sources-btn-remove-api-key"
          >
            Key entfernen
          </Button>
        ) : null}
        <Button type="submit" data-testid="sources-btn-save-api-key">
          Speichern
        </Button>
      </DialogFooter>
    </form>
  );
}

/** Dialog zum Hinterlegen eines API-Keys; ein gespeicherter Key wird nie angezeigt. */
export function ApiKeyDialog({ source, error, onSave, onRemove, onClose }: ApiKeyDialogProps) {
  if (source === null) return null;
  return (
    <Dialog open onOpenChange={(open) => (open ? undefined : onClose())}>
      <DialogContent data-testid="sources-dialog-api-key">
        <DialogHeader>
          <DialogTitle>API-Key für {source.name}</DialogTitle>
          <DialogDescription>
            {source.hasApiKey
              ? "Ein Key ist hinterlegt. Ein neuer Key ersetzt ihn."
              : "Noch kein Key hinterlegt."}
          </DialogDescription>
        </DialogHeader>
        {error ? (
          <p role="alert" className="text-sm text-destructive" data-testid="sources-error-save">
            {error}
          </p>
        ) : null}
        <ApiKeyFormBody source={source} onSave={onSave} onRemove={onRemove} />
      </DialogContent>
    </Dialog>
  );
}
