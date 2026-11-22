import { useScanStatus as useSharedScanStatus } from "@/shared/hooks/use-scan-status";

// Nach einem Lauf ändern sich die Funde und der Stand der Anwendung.
const KEYS_AFTER_RUN = [["application-findings"], ["application"]] as const;

/** Stand des letzten Scans; teilt den Cache mit der Schwachstellen-Seite und pollt beim Lauf. */
export function useScanStatus() {
  return useSharedScanStatus(KEYS_AFTER_RUN);
}
