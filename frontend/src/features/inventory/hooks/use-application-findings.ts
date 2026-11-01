import { useQuery } from "@tanstack/react-query";

import { type ApplicationFindingsPage, listApplicationFindings } from "../api/inventory-api";
import type { CveFilters } from "../model/cve-filters";

export function useApplicationFindings(applicationId: number, filters: CveFilters) {
  return useQuery({
    queryKey: ["application-findings", applicationId, filters],
    queryFn: () => listApplicationFindings(applicationId, filters),
    // Alte Liste nur beim Umfiltern derselben Anwendung behalten, nie beim Wechsel.
    placeholderData: (previous: ApplicationFindingsPage | undefined, previousQuery) =>
      previousQuery?.queryKey[1] === applicationId ? previous : undefined,
  });
}
