import { zodResolver } from "@hookform/resolvers/zod";
import { useState, type ChangeEvent } from "react";
import { type UseFormRegisterReturn, useForm } from "react-hook-form";

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

import { readSbomFile, type SbomFile, SbomFileError } from "../model/sbom-file";
import { type SbomUploadInput, sbomUploadSchema } from "../model/sbom-schema";
import type { SbomUploadBody } from "../model/sbom-types";

const MISSING_FILE = "Bitte eine SBOM-Datei wählen.";
const UNREADABLE_FILE = "Die Datei konnte nicht gelesen werden.";

interface SbomUploadDialogProps {
  open: boolean;
  /** Gesetzt bei „Neue Version“: der Name steht fest. */
  fixedName: string | null;
  isSubmitting: boolean;
  error: string | null;
  onSubmit: (body: SbomUploadBody) => void;
  onOpenChange: (open: boolean) => void;
}

type FormProps = Pick<SbomUploadDialogProps, "fixedName" | "isSubmitting" | "onSubmit">;

/** Liest die gewählte Datei ein und meldet den Inhalt oder einen Fehler. */
function useSbomFile(onRead: (sbom: SbomFile) => void) {
  const [document, setDocument] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  const choose = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    setDocument(null);
    if (!file) return;
    try {
      const sbom = await readSbomFile(file);
      setDocument(sbom.document);
      setError(null);
      onRead(sbom);
    } catch (readError) {
      setError(readError instanceof SbomFileError ? readError.message : UNREADABLE_FILE);
    }
  };
  const requireDocument = () => {
    if (document === null) setError((current) => current ?? MISSING_FILE);
    return document;
  };
  return { choose, error, requireDocument };
}

interface TextFieldProps {
  id: string;
  label: string;
  error?: string;
  readOnly?: boolean;
  description?: string;
  registration: UseFormRegisterReturn;
}

function TextField({ id, label, error, readOnly, description, registration }: TextFieldProps) {
  return (
    <Field data-invalid={Boolean(error)}>
      <FieldLabel htmlFor={id}>{label}</FieldLabel>
      <Input
        id={id}
        readOnly={readOnly}
        aria-invalid={Boolean(error)}
        data-testid={`inventory-input-${id}`}
        {...registration}
      />
      {description && <FieldDescription>{description}</FieldDescription>}
      {error && <FieldError data-testid={`inventory-error-${id}`}>{error}</FieldError>}
    </Field>
  );
}

function FileField({
  error,
  onChange,
}: {
  error: string | null;
  onChange: (event: ChangeEvent<HTMLInputElement>) => void;
}) {
  return (
    <Field data-invalid={Boolean(error)}>
      <FieldLabel htmlFor="sbom-file">CycloneDX-Datei (JSON)</FieldLabel>
      <Input
        id="sbom-file"
        type="file"
        accept=".json,application/json"
        onChange={onChange}
        data-testid="inventory-input-sbom-file"
      />
      {error && <FieldError data-testid="inventory-error-sbom-file">{error}</FieldError>}
    </Field>
  );
}

function SbomUploadForm({ fixedName, isSubmitting, onSubmit }: FormProps) {
  const form = useForm<SbomUploadInput>({
    resolver: zodResolver(sbomUploadSchema),
    defaultValues: { name: fixedName ?? "", label: "" },
  });
  const file = useSbomFile((sbom) => {
    if (fixedName === null) form.setValue("name", sbom.suggestedName);
    form.setValue("label", sbom.suggestedLabel);
  });
  const submit = form.handleSubmit(({ name, label }) => {
    const document = file.requireDocument();
    if (document) onSubmit({ name, label: label.trim() || null, document });
  });
  const { errors } = form.formState;

  return (
    <form
      onSubmit={submit}
      noValidate
      className="flex flex-col gap-4"
      data-testid="inventory-form-sbom-upload"
    >
      <FileField error={file.error} onChange={(event) => void file.choose(event)} />
      <TextField
        id="sbom-name"
        label="Name"
        readOnly={fixedName !== null}
        error={errors.name?.message}
        registration={form.register("name")}
      />
      <TextField
        id="sbom-label"
        label="Versionsbezeichnung"
        description="Leer lassen: aus der SBOM bzw. Upload-Zeitpunkt."
        error={errors.label?.message}
        registration={form.register("label")}
      />
      <DialogFooter>
        <Button type="submit" disabled={isSubmitting} data-testid="inventory-btn-sbom-submit">
          Hochladen
        </Button>
      </DialogFooter>
    </form>
  );
}

/** Dialog zum Hochladen einer SBOM bzw. einer neuen Version einer vorhandenen SBOM. */
export function SbomUploadDialog({
  open,
  error,
  onOpenChange,
  ...formProps
}: SbomUploadDialogProps) {
  const title = formProps.fixedName ? `Neue Version von ${formProps.fixedName}` : "SBOM hochladen";
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent data-testid="inventory-dialog-sbom-upload">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>
            Die bisherige Version wird archiviert. Geprüft wird nur die aktuelle Version.
          </DialogDescription>
        </DialogHeader>
        {error && (
          <p
            role="alert"
            className="text-sm text-destructive"
            data-testid="inventory-error-sbom-upload"
          >
            {error}
          </p>
        )}
        {open && <SbomUploadForm {...formProps} />}
      </DialogContent>
    </Dialog>
  );
}
