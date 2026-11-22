import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";

import { HttpError } from "@/shared/api/http-client";
import { fetchScanStatus, SCAN_STATUS_QUERY_KEY, startScan } from "@/shared/api/scan-status";


const POLL_INTERVAL_MS = 2000;
const HTTP_CONFLICT = 409;
// Nach einem Lauf ändern sich Funde und der Stand der Quellen.
const KEYS_AFTER_RUN = [["findings"], ["sources"]] as const;

/** Zustand des Hintergrund-Scans; pollt, solange er läuft. */
export function useIngestStatus() {
  const queryClient = useQueryClient();
  const status = useQuery({
    queryKey: SCAN_STATUS_QUERY_KEY,
    queryFn: fetchScanStatus,
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
    mutationFn: startScan,
    onSuccess: (state) => {
      queryClient.setQueryData(SCAN_STATUS_QUERY_KEY, state);
      void queryClient.invalidateQueries({ queryKey: ["sources"] });
    },
  });
}

export function isAlreadyRunning(error: unknown): boolean {
  return error instanceof HttpError && error.status === HTTP_CONFLICT;
}
