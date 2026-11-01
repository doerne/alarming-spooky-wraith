import { z } from "zod";

export const riskLevelSchema = z.enum(["kritisch", "hoch", "mittel", "niedrig"]);
export type RiskLevel = z.infer<typeof riskLevelSchema>;

export const findingSchema = z.object({
  advisoryId: z.string(),
  cveId: z.string().nullable(),
  title: z.string(),
  applicationName: z.string(),
  componentName: z.string(),
  componentVersion: z.string(),
  ecosystem: z.string().nullable(),
  riskScore: z.number(),
  riskLevel: riskLevelSchema,
  fixVersion: z.string().nullable(),
  status: z.string(),
});
export type Finding = z.infer<typeof findingSchema>;

export const findingsPageSchema = z.object({
  items: z.array(findingSchema),
  total: z.number(),
});
export type FindingsPage = z.infer<typeof findingsPageSchema>;

export const ingestStateSchema = z.object({
  running: z.boolean(),
  startedAt: z.string().nullable(),
  finishedAt: z.string().nullable(),
  componentsScanned: z.number().nullable(),
  findingsFound: z.number().nullable(),
  error: z.string().nullable(),
});
export type IngestState = z.infer<typeof ingestStateSchema>;
