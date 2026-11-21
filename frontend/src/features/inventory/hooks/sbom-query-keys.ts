import type { QueryClient } from "@tanstack/react-query";

export const sbomKeys = {
  list: (applicationId: number) => ["sboms", applicationId] as const,
  allVersions: (applicationId: number) => ["sbom-versions", applicationId] as const,
  allVersionDetails: (applicationId: number) => ["sbom-version", applicationId] as const,
};

/** Nach Upload oder Löschen ändern sich SBOMs, Komponenten und Treffer. */
export function invalidateAfterSbomChange(queryClient: QueryClient, applicationId: number) {
  for (const queryKey of [
    sbomKeys.list(applicationId),
    sbomKeys.allVersions(applicationId),
    ["application", applicationId],
    ["application-findings", applicationId],
    ["findings"],
  ]) {
    void queryClient.invalidateQueries({ queryKey });
  }
}
