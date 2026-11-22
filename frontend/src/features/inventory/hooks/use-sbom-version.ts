import { skipToken, useQuery } from "@tanstack/react-query";

import { getSbomVersion } from "../api/sbom-api";
import { sbomKeys } from "./sbom-query-keys";

export interface SbomVersionRef {
  sbomId: number;
  versionId: number;
}

export function useSbomVersion(applicationId: number, ref: SbomVersionRef | null) {
  return useQuery({
    queryKey: [...sbomKeys.allVersionDetails(applicationId), ref?.sbomId, ref?.versionId],
    queryFn:
      ref === null ? skipToken : () => getSbomVersion(applicationId, ref.sbomId, ref.versionId),
  });
}
