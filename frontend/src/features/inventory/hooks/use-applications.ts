import { useQuery } from "@tanstack/react-query";

import { listApplications } from "../api/inventory-api";

export function useApplications() {
  return useQuery({ queryKey: ["applications"], queryFn: listApplications });
}
