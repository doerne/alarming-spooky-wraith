import { useMutation, useQueryClient } from "@tanstack/react-query";

import { runIngest } from "../api/cves-api";

export function useRunIngest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: runIngest,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["findings"] }),
  });
}
