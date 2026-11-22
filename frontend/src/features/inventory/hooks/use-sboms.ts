import { useQuery } from "@tanstack/react-query";

import { listSboms } from "../api/sbom-api";
import { sbomKeys } from "./sbom-query-keys";

export function useSboms(applicationId: number) {
  return useQuery({
    queryKey: sbomKeys.list(applicationId),
    queryFn: () => listSboms(applicationId),
  });
}
