/** Zentrale Query-Keys, damit Abfragen und Invalidierungen dieselben Schlüssel nutzen. */
export const queryKeys = {
  applications: ["applications"] as const,
  findings: ["findings"] as const,
  /** Unter "findings", damit jede Änderung an Funden, Inventar oder Scan die Übersicht mit lädt. */
  applicationsOverview: ["findings", "applications-overview"] as const,
  applicationFindings: (applicationId: number) => ["application-findings", applicationId] as const,
  application: (applicationId: number) => ["application", applicationId] as const,
};
