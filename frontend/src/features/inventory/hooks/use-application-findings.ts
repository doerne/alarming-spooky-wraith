import { useQuery } from "@tanstack/react-query";

import { listApplicationFindings } from "../api/inventory-api";

export function useApplicationFindings(applicationId: number) {
  return useQuery({
    queryKey: ["application-findings", applicationId],
    queryFn: () => listApplicationFindings(applicationId),
  });
}
