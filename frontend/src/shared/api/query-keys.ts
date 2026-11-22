/** Zentrale Query-Keys, damit Abfragen und Invalidierungen dieselben Schlüssel nutzen. */
export const queryKeys = {
  findings: ["findings"] as const,
  applicationFindings: (applicationId: number) => ["application-findings", applicationId] as const,
  application: (applicationId: number) => ["application", applicationId] as const,
};
