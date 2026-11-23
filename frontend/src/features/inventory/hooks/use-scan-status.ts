import { queryKeys } from "@/shared/api/query-keys";
import { useScanStatus as useSharedScanStatus } from "@/shared/hooks/use-scan-status";

// Nach einem Lauf ändern sich die Funde, der Stand der Anwendung und die Übersicht.
const KEYS_AFTER_RUN = [
  ["application-findings"],
  ["application"],
  queryKeys.applicationsOverview,
] as const;

/** Stand des letzten Scans; teilt den Cache mit der Schwachstellen-Seite und pollt beim Lauf. */
export function useScanStatus(pollIntervalMs?: number) {
  return useSharedScanStatus(KEYS_AFTER_RUN, pollIntervalMs);
}
