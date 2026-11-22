import { queryKeys } from "@/shared/api/query-keys";
import { useEffect, useRef } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  type ApplicationGitHubInput,
  getGitHubStatus,
  startGitHubSync,
  updateApplicationGitHub,
} from "../api/github-api";
import type { GitHubLevel } from "../model/types";

const STATUS_POLL_MILLISECONDS = 2_000;

export function useGitHubStatus() {
  return useQuery({
    queryKey: ["github", "status"],
    queryFn: getGitHubStatus,
    refetchInterval: (query) => (query.state.data?.running ? STATUS_POLL_MILLISECONDS : false),
  });
}

export function useUpdateGitHubSettings(applicationId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: ApplicationGitHubInput) => updateApplicationGitHub(applicationId, input),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: queryKeys.application(applicationId) }),
  });
}

export function useStartGitHubSync(applicationId: number) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: { createIssues: boolean; minLevel: GitHubLevel | null }) =>
      startGitHubSync(applicationId, input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["github", "status"] }),
  });
}

/** Lädt die Anwendung neu, sobald ein Abgleich im Hintergrund fertig ist. */
export function useRefreshAfterSync(applicationId: number, running: boolean) {
  const queryClient = useQueryClient();
  const wasRunning = useRef(false);
  useEffect(() => {
    if (wasRunning.current && !running) {
      // Der Abgleich ändert Fund-Status: Tabelle und Verlauf (Anwendung und global) neu laden.
      void queryClient.invalidateQueries({ queryKey: queryKeys.application(applicationId) });
      void queryClient.invalidateQueries({
        queryKey: queryKeys.applicationFindings(applicationId),
      });
      void queryClient.invalidateQueries({ queryKey: queryKeys.findings });
    }
    wasRunning.current = running;
  }, [applicationId, running, queryClient]);
}
