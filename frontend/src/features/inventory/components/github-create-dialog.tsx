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
import { Field, FieldError, FieldLabel } from "@/shared/ui/field";

import { type GitHubCreateInput, githubCreateSchema } from "../model/github-schema";
import { GithubLevelSelect } from "./github-level-select";

interface GithubCreateDialogProps {
  isStarting: boolean;
  onConfirm: (input: GitHubCreateInput) => void;
  onCancel: () => void;
}

/** Fragt die Mindest-Risikostufe ab, ab der Issues angelegt werden. */
export function GithubCreateDialog({ isStarting, onConfirm, onCancel }: GithubCreateDialogProps) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<GitHubCreateInput>({
    resolver: zodResolver(githubCreateSchema),
    defaultValues: { minLevel: "hoch" },
  });

  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) onCancel();
      }}
    >
      <DialogContent data-testid="inventory-dialog-github-create">
        <DialogHeader>
          <DialogTitle>Issues in GitHub anlegen</DialogTitle>
          <DialogDescription>
            Legt für offene CVEs ab dieser Stufe ein Issue an, sofern noch keines existiert.
          </DialogDescription>
        </DialogHeader>
        <form
          onSubmit={handleSubmit((values) => onConfirm(values))}
          data-testid="inventory-form-github-create"
        >
          <Field>
            <FieldLabel htmlFor="github-create-min-level">Mindest-Risiko</FieldLabel>
            <GithubLevelSelect
              id="github-create-min-level"
              testId="inventory-select-github-min-level"
              registration={register("minLevel")}
            />
            {errors.minLevel && <FieldError>{errors.minLevel.message}</FieldError>}
          </Field>
          <DialogFooter>
            <Button variant="outline" onClick={onCancel} data-testid="inventory-btn-github-cancel">
              Abbrechen
            </Button>
            <Button
              type="submit"
              disabled={isStarting}
              data-testid="inventory-btn-github-create-confirm"
            >
              Anlegen starten
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
