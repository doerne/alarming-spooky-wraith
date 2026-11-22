import { queryKeys } from "@/shared/api/query-keys";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { deleteApplication } from "../api/inventory-api";

export function useDeleteApplication(applicationId: number) {
  const queryClient = useQueryClient();
  return useMutation<void, Error, void>({
    mutationFn: () => deleteApplication(applicationId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.applications });
      void queryClient.invalidateQueries({ queryKey: queryKeys.findings });
      // Die gelöschte Anwendung nicht neu laden (wäre 404), nur als veraltet markieren.
      for (const queryKey of [
        queryKeys.application(applicationId),
        queryKeys.applicationFindings(applicationId),
      ]) {
        void queryClient.invalidateQueries({ queryKey, refetchType: "none" });
      }
    },
  });
}
