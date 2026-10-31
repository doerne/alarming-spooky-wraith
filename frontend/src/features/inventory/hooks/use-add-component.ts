import { useMutation, useQueryClient } from "@tanstack/react-query";

import { addComponent } from "../api/inventory-api";
import type { ComponentInput } from "../model/schema";

interface AddComponentVars {
  applicationId: number;
  input: ComponentInput;
}

export function useAddComponent() {
  const queryClient = useQueryClient();
  return useMutation<void, Error, AddComponentVars>({
    mutationFn: ({ applicationId, input }) => addComponent(applicationId, input),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["findings"] }),
  });
}
