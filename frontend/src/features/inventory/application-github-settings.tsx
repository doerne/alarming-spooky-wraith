import { Github } from "lucide-react";

import { Button } from "@/shared/ui/button";

import { GithubSettingsDialog } from "./components/github-settings-dialog";
import { useGithubSettingsDialog } from "./hooks/use-github-settings-dialog";

import type { ApplicationDetail } from "./model/types";

interface ApplicationGithubSettingsProps {
  applicationId: number;
  application: ApplicationDetail | undefined;
}

/** GitHub-Einstellungen einer Anwendung: Knopf im Kopf und Dialog mit Repository und Automatik. */
export function ApplicationGithubSettings({
  applicationId,
  application,
}: ApplicationGithubSettingsProps) {
  const settings = useGithubSettingsDialog(applicationId);
  return (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={settings.openDialog}
        disabled={!application}
        data-testid="inventory-btn-github-settings"
      >
        <Github /> GitHub
      </Button>
      {settings.open && application && (
        <GithubSettingsDialog
          repository={application.githubRepository}
          autoIssueMinLevel={application.autoIssueMinLevel}
          isSaving={settings.isSaving}
          error={settings.error}
          onSave={settings.save}
          onCancel={settings.closeDialog}
        />
      )}
    </>
  );
}
