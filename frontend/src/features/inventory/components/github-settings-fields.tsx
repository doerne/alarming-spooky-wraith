import type { UseFormRegisterReturn } from "react-hook-form";

import { Field, FieldError, FieldLabel } from "@/shared/ui/field";
import { Input } from "@/shared/ui/input";

import { GithubLevelSelect } from "./github-level-select";

export function RepositoryField({
  registration,
  message,
}: {
  registration: UseFormRegisterReturn;
  message: string | undefined;
}) {
  return (
    <Field>
      <FieldLabel htmlFor="github-settings-repository">Repository</FieldLabel>
      <Input
        id="github-settings-repository"
        placeholder="owner/repo"
        data-testid="inventory-input-github-repository"
        {...registration}
      />
      {message && (
        <FieldError data-testid="inventory-error-github-repository">{message}</FieldError>
      )}
    </Field>
  );
}

export function AutoLevelField({ registration }: { registration: UseFormRegisterReturn }) {
  return (
    <Field>
      <FieldLabel htmlFor="github-settings-auto-level">Neue CVEs automatisch anlegen ab</FieldLabel>
      <GithubLevelSelect
        id="github-settings-auto-level"
        testId="inventory-select-github-auto-level"
        registration={registration}
        emptyLabel="aus"
      />
    </Field>
  );
}
