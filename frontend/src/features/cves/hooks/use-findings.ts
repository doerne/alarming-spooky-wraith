import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { fetchFilteredFindings, fetchFindings } from "../api/cves-api";
import type { FindingFilters } from "../model/filters";

/** Alle Funde (ungefiltert) – für Kacheln und Diagramm. */
export function useFindings() {
  return useQuery({ queryKey: ["findings", "all"], queryFn: fetchFindings });
}

/** Gefilterte Funde für die Tabelle; behält beim Umfiltern die alte Liste bis zur Antwort. */
export function useFilteredFindings(filters: FindingFilters) {
  return useQuery({
    queryKey: ["findings", "filtered", filters],
    queryFn: () => fetchFilteredFindings(filters),
    placeholderData: keepPreviousData,
  });
}
