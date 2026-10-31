import { useQuery } from "@tanstack/react-query";

import { getApplication } from "../api/inventory-api";

export function useApplication(applicationId: number) {
  return useQuery({
    queryKey: ["application", applicationId],
    queryFn: () => getApplication(applicationId),
  });
}
