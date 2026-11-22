import { z } from "zod";

import { request } from "./http-client";

export const CLOSURE_KINDS = [
  "fixed_confirmed",
  "fixed_reported",
  "fixed_manual",
  "accepted",
  "false_positive",
] as const;
export type ClosureKind = (typeof CLOSURE_KINDS)[number];

export const CLOSURE_KIND_LABELS: Record<ClosureKind, string> = {
  fixed_confirmed: "Behoben, bestätigt",
  fixed_reported: "Behoben, gemeldet",
  fixed_manual: "Behoben, von Hand",
  accepted: "Akzeptiert",
  false_positive: "False Positive",
};

export const remediationKpisSchema = z.object({
  deadlines: z.object({
    overdue: z.number(),
    dueSoon: z.number(),
    overdueBySeverity: z.object({
      kritisch: z.number(),
      hoch: z.number(),
      mittel: z.number(),
      niedrig: z.number(),
    }),
    nextDueAt: z.string().nullable(),
  }),
  updates: z.object({
    targets: z.array(
      z.object({
        packageName: z.string(),
        ecosystem: z.string().nullable(),
        targetVersion: z.string(),
        findings: z.number(),
        applications: z.number(),
      }),
    ),
    fixableOpen: z.number(),
    openTotal: z.number(),
    morePackages: z.number(),
  }),
});
export type RemediationKpis = z.infer<typeof remediationKpisSchema>;

export async function fetchRemediationKpis({
  applicationId,
}: {
  applicationId?: number;
}): Promise<RemediationKpis> {
  const query = applicationId === undefined ? "" : `?applicationId=${applicationId}`;
  return remediationKpisSchema.parse(await request(`/api/findings/kpis${query}`));
}
