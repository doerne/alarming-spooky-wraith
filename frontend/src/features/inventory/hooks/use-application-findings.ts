import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { listApplicationFindings } from "../api/inventory-api";
import type { CveFilters } from "../model/cve-filters";

export function useApplicationFindings(applicationId: number, filters: CveFilters) {
  return useQuery({
    queryKey: ["application-findings", applicationId, filters],
    queryFn: () => listApplicationFindings(applicationId, filters),
    placeholderData: keepPreviousData,
  });
}
