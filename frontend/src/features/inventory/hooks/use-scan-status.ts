import { useQuery } from "@tanstack/react-query";

import { fetchScanStatus, SCAN_STATUS_QUERY_KEY } from "@/shared/api/scan-status";

/** Stand des letzten Scans; teilt den Cache mit der Schwachstellen-Seite. */
export function useScanStatus() {
  return useQuery({ queryKey: SCAN_STATUS_QUERY_KEY, queryFn: fetchScanStatus });
}
