import { z } from "zod";

export const riskLevelSchema = z.enum(["kritisch", "hoch", "mittel", "niedrig"]);
export type RiskLevel = z.infer<typeof riskLevelSchema>;

export const findingSchema = z.object({
  advisoryId: z.string(),
  cveId: z.string().nullable(),
  title: z.string(),
  applicationId: z.number(),
  applicationName: z.string(),
  componentId: z.number(),
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
  unfilteredTotal: z.number(),
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

export const affectedFindingSchema = z.object({
  applicationName: z.string(),
  componentId: z.number(),
  componentName: z.string(),
  foundVersion: z.string(),
  ecosystem: z.string().nullable(),
  riskScore: z.number(),
  riskLevel: riskLevelSchema,
  status: z.string(),
});

export const cveDetailSchema = z.object({
  advisoryId: z.string(),
  cveId: z.string().nullable(),
  title: z.string(),
  cvssBase: z.number().nullable(),
  fixVersion: z.string().nullable(),
  riskScore: z.number(),
  riskLevel: riskLevelSchema,
  description: z.string(),
  rationale: z.string(),
  references: z.array(z.string()),
  sources: z.array(z.object({ sourceKey: z.string(), url: z.string() })),
  findings: z.array(affectedFindingSchema),
});
export type CveDetail = z.infer<typeof cveDetailSchema>;
