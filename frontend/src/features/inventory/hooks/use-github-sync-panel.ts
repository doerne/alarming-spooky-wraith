import { useState } from "react";

import type { GitHubStatus } from "../api/github-api";
import { githubSyncHint } from "../model/github-hint";
import type { GitHubCreateInput } from "../model/github-schema";
import type { ApplicationDetail } from "../model/types";
import { useApplication } from "./use-application";
import { useGitHubStatus, useRefreshAfterSync, useStartGitHubSync } from "./use-github";

function isRunning(status: GitHubStatus | undefined, starting: boolean): boolean {
  return (status?.running ?? false) || starting;
}

function syncFields(detail: ApplicationDetail | undefined) {
  return {
    repository: detail?.githubRepository ?? null,
    lastSyncedAt: detail?.githubSyncedAt ?? null,
    lastSyncMessage: detail?.githubSyncMessage ?? "",
  };
}

/** Zustand des GitHub-Blocks im CVE-Reiter: Verfügbarkeit, Start, Anlege-Dialog. */
export function useGithubSyncPanel(applicationId: number) {
  const detail = useApplication(applicationId);
  const status = useGitHubStatus();
  const startSync = useStartGitHubSync(applicationId);
  const [createOpen, setCreateOpen] = useState(false);
  const running = isRunning(status.data, startSync.isPending);
  useRefreshAfterSync(applicationId, running);
  const fields = syncFields(detail.data);

  const confirmCreate = ({ minLevel }: GitHubCreateInput) => {
    startSync.mutate({ createIssues: true, minLevel });
    setCreateOpen(false);
  };

  return {
    controls: {
      hint: githubSyncHint({
        repository: fields.repository,
        configured: status.data?.configured ?? false,
        running,
      }),
      lastSyncedAt: fields.lastSyncedAt,
      lastSyncMessage: fields.lastSyncMessage,
      error: startSync.error?.message ?? null,
      onOpenCreate: () => setCreateOpen(true),
      onSync: () => startSync.mutate({ createIssues: false, minLevel: null }),
    },
    createOpen,
    isStarting: startSync.isPending,
    closeCreate: () => setCreateOpen(false),
    confirmCreate,
  };
}
