import { useQuery } from "@tanstack/react-query";

import { fetchFindings } from "../api/cves-api";

export function useFindings() {
  return useQuery({ queryKey: ["findings"], queryFn: fetchFindings });
}
