import { type QueryKey, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef } from "react";

import { fetchScanStatus, SCAN_STATUS_QUERY_KEY } from "@/shared/api/scan-status";

const POLL_INTERVAL_MS = 2000;

/**
 * Zustand des Hintergrund-Scans; pollt, solange er läuft, und frischt danach die
 * übergebenen Abfragen auf (jedes Feature nennt seine eigenen).
 */
export function useScanStatus(
  keysAfterRun: ReadonlyArray<QueryKey>,
  pollIntervalMs: number = POLL_INTERVAL_MS,
) {
  const queryClient = useQueryClient();
  const status = useQuery({
    queryKey: SCAN_STATUS_QUERY_KEY,
    queryFn: fetchScanStatus,
    refetchInterval: (query) => (query.state.data?.running ? pollIntervalMs : false),
  });
  const wasRunning = useRef(false);
  const running = status.data?.running ?? false;

  useEffect(() => {
    if (wasRunning.current && !running) {
      for (const queryKey of keysAfterRun) void queryClient.invalidateQueries({ queryKey });
    }
    wasRunning.current = running;
  }, [running, queryClient, keysAfterRun]);

  return status;
}
