import { skipToken, useQuery } from "@tanstack/react-query";

import { listSbomVersions } from "../api/sbom-api";
import { sbomKeys } from "./sbom-query-keys";

export function useSbomVersions(applicationId: number, sbomId: number | null) {
  return useQuery({
    queryKey: [...sbomKeys.allVersions(applicationId), sbomId],
    queryFn: sbomId === null ? skipToken : () => listSbomVersions(applicationId, sbomId),
  });
}
