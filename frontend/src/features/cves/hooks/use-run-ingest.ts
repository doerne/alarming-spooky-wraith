import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";

import { HttpError } from "@/shared/api/http-client";

import { fetchIngestStatus, startIngest } from "../api/cves-api";

const INGEST_STATUS_KEY = ["ingest-status"] as const;
const POLL_INTERVAL_MS = 2000;
const HTTP_CONFLICT = 409;
// Nach einem Lauf ändern sich Funde und der Stand der Quellen.
const KEYS_AFTER_RUN = [["findings"], ["sources"]] as const;

/** Zustand des Hintergrund-Scans; pollt, solange er läuft. */
export function useIngestStatus() {
  const queryClient = useQueryClient();
  const status = useQuery({
    queryKey: INGEST_STATUS_KEY,
    queryFn: fetchIngestStatus,
    refetchInterval: (query) => (query.state.data?.running ? POLL_INTERVAL_MS : false),
  });
  const wasRunning = useRef(false);
  const running = status.data?.running ?? false;

  useEffect(() => {
    if (wasRunning.current && !running) {
      for (const queryKey of KEYS_AFTER_RUN) void queryClient.invalidateQueries({ queryKey });
    }
    wasRunning.current = running;
  }, [running, queryClient]);

  return status;
}

export function useStartIngest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: startIngest,
    onSuccess: (state) => {
      queryClient.setQueryData(INGEST_STATUS_KEY, state);
      void queryClient.invalidateQueries({ queryKey: ["sources"] });
    },
  });
}

export function isAlreadyRunning(error: unknown): boolean {
  return error instanceof HttpError && error.status === HTTP_CONFLICT;
}
