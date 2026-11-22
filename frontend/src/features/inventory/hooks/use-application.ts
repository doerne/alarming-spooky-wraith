import { queryKeys } from "@/shared/api/query-keys";
import { useQuery } from "@tanstack/react-query";

import { getApplication } from "../api/inventory-api";

export function useApplication(applicationId: number) {
  return useQuery({
    queryKey: queryKeys.application(applicationId),
    queryFn: () => getApplication(applicationId),
  });
}
