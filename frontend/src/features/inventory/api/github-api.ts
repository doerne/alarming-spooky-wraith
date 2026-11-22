import { request } from "@/shared/api/http-client";

import type { ApplicationDetail, GitHubLevel } from "../model/types";

export interface GitHubStatus {
  configured: boolean;
  running: boolean;
}

export interface GitHubSyncState {
  running: boolean;
  startedAt: string | null;
  finishedAt: string | null;
  error: string | null;
}

export interface ApplicationGitHubInput {
  githubRepository: string | null;
  autoIssueMinLevel: GitHubLevel | null;
}

export async function getGitHubStatus(): Promise<GitHubStatus> {
  return request<GitHubStatus>("/api/github/status");
}

export async function updateApplicationGitHub(
  applicationId: number,
  input: ApplicationGitHubInput,
): Promise<ApplicationDetail> {
  return request<ApplicationDetail>(`/api/applications/${applicationId}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export async function startGitHubSync(
  applicationId: number,
  input: { createIssues: boolean; minLevel: GitHubLevel | null },
): Promise<GitHubSyncState> {
  return request<GitHubSyncState>(`/api/applications/${applicationId}/github/sync`, {
    method: "POST",
    body: JSON.stringify(input),
  });
}
