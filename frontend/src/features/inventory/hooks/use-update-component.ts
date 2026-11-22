import { queryKeys } from "@/shared/api/query-keys";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { updateComponent } from "../api/inventory-api";
import type { ComponentInput } from "../model/schema";

interface UpdateComponentVars {
  applicationId: number;
  componentId: number;
  input: ComponentInput;
}

export function useUpdateComponent() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, UpdateComponentVars>({
    mutationFn: ({ applicationId, componentId, input }) =>
      updateComponent(applicationId, componentId, input),
    onSuccess: (_data, { applicationId }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.application(applicationId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.applicationFindings(applicationId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.findings });
    },
  });
}
