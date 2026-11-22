import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { fetchFindingTrend, type TrendWeeks } from "@/shared/api/finding-trend";

/** Wochentrend aller Funde; der Schlüssel liegt unter "findings" und wird mit invalidiert. */
export function useFindingTrend(weeks: TrendWeeks) {
  return useQuery({
    queryKey: ["findings", "trend", weeks],
    queryFn: () => fetchFindingTrend({ weeks }),
    placeholderData: keepPreviousData,
  });
}
