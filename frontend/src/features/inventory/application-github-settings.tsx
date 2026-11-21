import { Github } from "lucide-react";

import { Button } from "@/shared/ui/button";

import { GithubSettingsDialog } from "./components/github-settings-dialog";
import { useApplication } from "./hooks/use-application";
import { useGithubSettingsDialog } from "./hooks/use-github-settings-dialog";

interface ApplicationGithubSettingsProps {
  applicationId: number;
}

/** GitHub-Einstellungen einer Anwendung: Knopf im Kopf und Dialog mit Repository und Automatik. */
export function ApplicationGithubSettings({ applicationId }: ApplicationGithubSettingsProps) {
  const detail = useApplication(applicationId);
  const settings = useGithubSettingsDialog(applicationId);
  const application = detail.data;
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
