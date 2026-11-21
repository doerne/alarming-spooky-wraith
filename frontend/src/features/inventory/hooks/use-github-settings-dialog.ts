import { useState } from "react";

import type { GitHubSettingsInput } from "../model/github-schema";
import { useUpdateGitHubSettings } from "./use-github";

/** Zustand des GitHub-Einstellungsdialogs einer Anwendung. */
export function useGithubSettingsDialog(applicationId: number) {
  const [open, setOpen] = useState(false);
  const update = useUpdateGitHubSettings(applicationId);

  const save = (input: GitHubSettingsInput) => {
    update.mutate(
      {
        githubRepository: input.repository || null,
        autoIssueMinLevel: input.autoIssueMinLevel || null,
      },
      { onSuccess: () => setOpen(false) },
    );
  };

  return {
    open,
    openDialog: () => setOpen(true),
    closeDialog: () => setOpen(false),
    save,
    isSaving: update.isPending,
    error: update.error?.message ?? null,
  };
}
