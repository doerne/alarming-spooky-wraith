import { queryKeys } from "@/shared/api/query-keys";
import { useQuery } from "@tanstack/react-query";

import { listApplicationsOverview } from "../api/inventory-api";

export function useApplicationsOverview() {
  return useQuery({ queryKey: queryKeys.applicationsOverview, queryFn: listApplicationsOverview });
}
