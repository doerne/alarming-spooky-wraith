import { queryKeys } from "@/shared/api/query-keys";
import { useQuery } from "@tanstack/react-query";

import { listApplications } from "../api/inventory-api";

export function useApplications() {
  return useQuery({ queryKey: queryKeys.applications, queryFn: listApplications });
}
