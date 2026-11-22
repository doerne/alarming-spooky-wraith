import { queryKeys } from "@/shared/api/query-keys";
import { useQuery } from "@tanstack/react-query";

import { fetchRemediationKpis } from "@/shared/api/remediation-kpis";

/** Fristen- und Update-Kennzahlen aller Funde; der Schlüssel liegt unter "findings" und wird mit invalidiert. */
export function useRemediationKpis() {
  return useQuery({
    queryKey: [...queryKeys.findings, "kpis"],
    queryFn: () => fetchRemediationKpis({}),
  });
}
