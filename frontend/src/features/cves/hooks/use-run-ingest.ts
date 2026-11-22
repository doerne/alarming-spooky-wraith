import { useMutation, useQueryClient } from "@tanstack/react-query";

import { HttpError } from "@/shared/api/http-client";
import { SCAN_STATUS_QUERY_KEY, startScan } from "@/shared/api/scan-status";
import { useScanStatus } from "@/shared/hooks/use-scan-status";

const HTTP_CONFLICT = 409;
// Nach einem Lauf ändern sich Funde und der Stand der Quellen.
const KEYS_AFTER_RUN = [["findings"], ["sources"]] as const;

/** Zustand des Hintergrund-Scans; pollt, solange er läuft. */
export function useIngestStatus() {
  return useScanStatus(KEYS_AFTER_RUN);
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
