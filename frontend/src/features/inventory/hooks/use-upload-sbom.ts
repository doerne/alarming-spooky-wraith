import { useMutation, useQueryClient } from "@tanstack/react-query";

import { uploadSbomVersion } from "../api/sbom-api";
import type { SbomUploadBody, SbomUploadResult } from "../model/sbom-types";
import { invalidateAfterSbomChange } from "./sbom-query-keys";

export function useUploadSbom(applicationId: number) {
  const queryClient = useQueryClient();
  return useMutation<SbomUploadResult, Error, SbomUploadBody>({
    mutationFn: (body) => uploadSbomVersion(applicationId, body),
    onSuccess: () => invalidateAfterSbomChange(queryClient, applicationId),
  });
}
