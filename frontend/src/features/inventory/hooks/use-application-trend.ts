import { queryKeys } from "@/shared/api/query-keys";
import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { fetchFindingTrend, type TrendWeeks } from "@/shared/api/finding-trend";

/** Wochentrend einer Anwendung; der Schlüssel liegt unter "application-findings" und wird mit invalidiert. */
export function useApplicationTrend(applicationId: number, weeks: TrendWeeks) {
  return useQuery({
    queryKey: [...queryKeys.applicationFindings(applicationId), "trend", weeks],
    queryFn: () => fetchFindingTrend({ weeks, applicationId }),
    placeholderData: keepPreviousData,
  });
}
