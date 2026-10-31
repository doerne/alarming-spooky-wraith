import { useMutation } from "@tanstack/react-query";

import { type Application, createApplication } from "../api/inventory-api";

export function useCreateApplication() {
  return useMutation<Application, Error, { name: string }>({
    mutationFn: createApplication,
  });
}
