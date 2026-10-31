import { useMutation, useQueryClient } from "@tanstack/react-query";

import { type Application, createApplication } from "../api/inventory-api";

export function useCreateApplication() {
  const queryClient = useQueryClient();
  return useMutation<Application, Error, { name: string }>({
    mutationFn: createApplication,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["applications"] }),
  });
}
