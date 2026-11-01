import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  fetchSources,
  removeSourceApiKey,
  setSourceApiKey,
  setSourceEnabled,
} from "../api/sources-api";
import type { Source } from "../model/types";

export const SOURCES_KEY = ["sources"] as const;
const POLL_INTERVAL_MS = 2000;

function isRunning(sources: Source[] | undefined): boolean {
  return (sources ?? []).some((source) => source.lastStatus === "running");
}

/** Lädt die Quellen; solange ein Lauf aktiv ist, wird regelmäßig nachgeladen. */
export function useSources() {
  return useQuery({
    queryKey: SOURCES_KEY,
    queryFn: fetchSources,
    refetchInterval: (query) => (isRunning(query.state.data) ? POLL_INTERVAL_MS : false),
  });
}

function useInvalidateSources() {
  const queryClient = useQueryClient();
  return () => queryClient.invalidateQueries({ queryKey: SOURCES_KEY });
}

export function useSetSourceEnabled() {
  const invalidate = useInvalidateSources();
  return useMutation({ mutationFn: setSourceEnabled, onSuccess: invalidate });
}

export function useSetSourceApiKey() {
  const invalidate = useInvalidateSources();
  return useMutation({ mutationFn: setSourceApiKey, onSuccess: invalidate });
}

export function useRemoveSourceApiKey() {
  const invalidate = useInvalidateSources();
  return useMutation({ mutationFn: removeSourceApiKey, onSuccess: invalidate });
}
