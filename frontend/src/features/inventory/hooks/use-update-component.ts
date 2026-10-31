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
      queryClient.invalidateQueries({ queryKey: ["application", applicationId] });
      queryClient.invalidateQueries({ queryKey: ["application-findings", applicationId] });
      queryClient.invalidateQueries({ queryKey: ["findings"] });
    },
  });
}
