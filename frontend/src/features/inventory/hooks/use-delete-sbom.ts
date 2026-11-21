import { useMutation, useQueryClient } from "@tanstack/react-query";

import { deleteSbom } from "../api/sbom-api";
import { invalidateAfterSbomChange } from "./sbom-query-keys";

export function useDeleteSbom(applicationId: number) {
  const queryClient = useQueryClient();
  return useMutation<void, Error, number>({
    mutationFn: (sbomId) => deleteSbom(applicationId, sbomId),
    onSuccess: () => invalidateAfterSbomChange(queryClient, applicationId),
  });
}
