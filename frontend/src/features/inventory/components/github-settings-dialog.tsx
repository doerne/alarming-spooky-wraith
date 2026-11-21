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

import { type GitHubSettingsInput, githubSettingsSchema } from "../model/github-schema";
import type { GitHubLevel } from "../model/types";
import { AutoLevelField, RepositoryField } from "./github-settings-fields";

interface GithubSettingsDialogProps {
  repository: string | null;
  autoIssueMinLevel: GitHubLevel | null;
  isSaving: boolean;
  error: string | null;
  onSave: (input: GitHubSettingsInput) => void;
  onCancel: () => void;
}

/** Repository und Automatik-Schwelle einer Anwendung; „aus“ schaltet die Automatik ab. */
export function GithubSettingsDialog({
  repository,
  autoIssueMinLevel,
  isSaving,
  error,
  onSave,
  onCancel,
}: GithubSettingsDialogProps) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<GitHubSettingsInput>({
    resolver: zodResolver(githubSettingsSchema),
    defaultValues: settingsDefaults(repository, autoIssueMinLevel),
  });

  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) onCancel();
      }}
    >
      <DialogContent data-testid="inventory-dialog-github-settings">
        <SettingsHeading />
        <form
          onSubmit={handleSubmit((values) => onSave(values))}
          data-testid="inventory-form-github-settings"
          className="flex flex-col gap-4"
        >
          <RepositoryField
            registration={register("repository")}
            message={errors.repository?.message}
          />
          <AutoLevelField registration={register("autoIssueMinLevel")} />
          <SettingsError message={error} />
          <DialogFooter>
            <Button
              variant="outline"
              onClick={onCancel}
              data-testid="inventory-btn-github-settings-cancel"
            >
              Abbrechen
            </Button>
            <Button
              type="submit"
              disabled={isSaving}
              data-testid="inventory-btn-github-settings-save"
            >
              Speichern
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function SettingsHeading() {
  return (
    <DialogHeader>
      <DialogTitle>GitHub-Anbindung</DialogTitle>
      <DialogDescription>
        Repository der Anwendung und Automatik für neu entdeckte CVEs.
      </DialogDescription>
    </DialogHeader>
  );
}

function settingsDefaults(
  repository: string | null,
  level: GitHubLevel | null,
): GitHubSettingsInput {
  return { repository: repository ?? "", autoIssueMinLevel: level ?? "" };
}

function SettingsError({ message }: { message: string | null }) {
  if (!message) return null;
  return (
    <p role="alert" className="text-sm text-destructive" data-testid="inventory-error-github-save">
      {message}
    </p>
  );
}
