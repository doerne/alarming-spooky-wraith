import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";

import { Button } from "@/shared/ui/button";
import { Field, FieldError, FieldLabel } from "@/shared/ui/field";
import { Input } from "@/shared/ui/input";

import { type ApplicationInput, applicationSchema } from "../model/schema";

export function ApplicationForm({ onCreate }: { onCreate: (values: ApplicationInput) => void }) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ApplicationInput>({
    resolver: zodResolver(applicationSchema),
    defaultValues: { name: "" },
  });

  return (
    <form
      onSubmit={handleSubmit(onCreate)}
      data-testid="inventory-form-application"
      className="flex items-end gap-3"
    >
      <Field>
        <FieldLabel htmlFor="inventory-app-name">Anwendung</FieldLabel>
        <Input
          id="inventory-app-name"
          data-testid="inventory-input-app-name"
          {...register("name")}
        />
        {errors.name && (
          <FieldError data-testid="inventory-error-app-name">{errors.name.message}</FieldError>
        )}
      </Field>
      <Button type="submit" data-testid="inventory-btn-create-app">
        Anlegen
      </Button>
    </form>
  );
}
