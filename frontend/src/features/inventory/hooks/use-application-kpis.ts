import { queryKeys } from "@/shared/api/query-keys";
import { useQuery } from "@tanstack/react-query";

import { fetchRemediationKpis } from "@/shared/api/remediation-kpis";

/** Fristen- und Update-Kennzahlen einer Anwendung; der Schlüssel liegt unter "application-findings" und wird mit invalidiert. */
export function useApplicationKpis(applicationId: number) {
  return useQuery({
    queryKey: [...queryKeys.applicationFindings(applicationId), "kpis"],
    queryFn: () => fetchRemediationKpis({ applicationId }),
  });
}
