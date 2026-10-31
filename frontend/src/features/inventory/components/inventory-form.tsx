import { zodResolver } from "@hookform/resolvers/zod";
import { type UseFormRegisterReturn, useForm } from "react-hook-form";

import { Button } from "@/shared/ui/button";
import { Field, FieldError, FieldLabel } from "@/shared/ui/field";
import { Input } from "@/shared/ui/input";

import { type ComponentInput, componentSchema } from "../model/schema";

const SELECT_CLASS =
  "border-input bg-transparent h-9 w-full rounded-md border px-3 py-1 text-sm shadow-xs";

interface TextFieldProps {
  id: string;
  label: string;
  testid: string;
  errorTestid: string;
  error?: string;
  registration: UseFormRegisterReturn;
}

function TextField({ id, label, testid, errorTestid, error, registration }: TextFieldProps) {
  return (
    <Field>
      <FieldLabel htmlFor={id}>{label}</FieldLabel>
      <Input id={id} data-testid={testid} {...registration} />
      {error && <FieldError data-testid={errorTestid}>{error}</FieldError>}
    </Field>
  );
}

function CategorySelect({ registration }: { registration: UseFormRegisterReturn }) {
  return (
    <Field>
      <FieldLabel htmlFor="inventory-category">Kategorie</FieldLabel>
      <select
        id="inventory-category"
        data-testid="inventory-select-category"
        className={SELECT_CLASS}
        {...registration}
      >
        <option value="language">Programmiersprache</option>
        <option value="framework">Framework</option>
        <option value="library">Library</option>
        <option value="service">Dienst/Produkt</option>
      </select>
    </Field>
  );
}

function EcosystemSelect({ registration }: { registration: UseFormRegisterReturn }) {
  return (
    <Field>
      <FieldLabel htmlFor="inventory-ecosystem">Ökosystem</FieldLabel>
      <select
        id="inventory-ecosystem"
        data-testid="inventory-select-ecosystem"
        className={SELECT_CLASS}
        {...registration}
      >
        <option value="">(keines)</option>
        <option value="npm">npm</option>
      </select>
    </Field>
  );
}

function DirectField({ registration }: { registration: UseFormRegisterReturn }) {
  return (
    <Field orientation="horizontal">
      <input
        type="checkbox"
        id="inventory-direct"
        data-testid="inventory-checkbox-direct"
        {...registration}
      />
      <FieldLabel htmlFor="inventory-direct">Direkte Abhängigkeit</FieldLabel>
    </Field>
  );
}

interface InventoryFormProps {
  onSubmit: (values: ComponentInput) => void;
  initialValues?: ComponentInput;
  submitLabel?: string;
  isSubmitting?: boolean;
  onCancel?: () => void;
}

const EMPTY_COMPONENT: ComponentInput = {
  name: "",
  version: "",
  category: "library",
  ecosystem: null,
  direct: true,
};

interface FormActionsProps {
  submitLabel: string;
  isSubmitting?: boolean;
  onCancel?: () => void;
}

function FormActions({ submitLabel, isSubmitting, onCancel }: FormActionsProps) {
  return (
    <div className="flex gap-3">
      <Button type="submit" disabled={isSubmitting} data-testid="inventory-btn-submit">
        {submitLabel}
      </Button>
      {onCancel && (
        <Button
          type="button"
          variant="outline"
          onClick={onCancel}
          data-testid="inventory-btn-cancel"
        >
          Abbrechen
        </Button>
      )}
    </div>
  );
}

export function InventoryForm({
  onSubmit,
  initialValues,
  submitLabel = "Komponente hinzufügen",
  isSubmitting,
  onCancel,
}: InventoryFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ComponentInput>({
    resolver: zodResolver(componentSchema),
    defaultValues: initialValues ?? EMPTY_COMPONENT,
  });

  return (
    <form
      onSubmit={handleSubmit(onSubmit)}
      data-testid="inventory-form-component"
      className="flex flex-col gap-4"
    >
      <TextField
        id="inventory-name"
        label="Name"
        testid="inventory-input-name"
        errorTestid="inventory-error-name"
        error={errors.name?.message}
        registration={register("name")}
      />
      <TextField
        id="inventory-version"
        label="Version"
        testid="inventory-input-version"
        errorTestid="inventory-error-version"
        error={errors.version?.message}
        registration={register("version")}
      />
      <CategorySelect registration={register("category")} />
      <EcosystemSelect
        registration={register("ecosystem", {
          setValueAs: (value: string) => (value === "" ? null : value),
        })}
      />
      <DirectField registration={register("direct")} />
      <FormActions submitLabel={submitLabel} isSubmitting={isSubmitting} onCancel={onCancel} />
    </form>
  );
}
