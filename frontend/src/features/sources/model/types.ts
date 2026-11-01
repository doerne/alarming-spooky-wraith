import { z } from "zod";

export const sourceStatusSchema = z.enum(["ready", "missing_key", "disabled"]);
export const runStatusSchema = z.enum(["running", "ok", "error", "skipped"]);
export const apiKeyRequirementSchema = z.enum(["none", "optional", "required"]);

export const sourceSchema = z.object({
  key: z.string(),
  name: z.string(),
  homepageUrl: z.string(),
  description: z.string(),
  kind: z.enum(["package_query", "bulk"]),
  scope: z.enum(["package", "product", "name"]),
  apiKeyRequirement: apiKeyRequirementSchema,
  apiKeyHint: z.string(),
  hasApiKey: z.boolean(),
  enabled: z.boolean(),
  status: sourceStatusSchema,
  lastRunAt: z.string().nullable(),
  lastStatus: runStatusSchema.nullable(),
  lastMessage: z.string(),
  lastFindings: z.number().nullable(),
});
export type Source = z.infer<typeof sourceSchema>;
export type SourceStatus = z.infer<typeof sourceStatusSchema>;

export const sourcesSchema = z.array(sourceSchema);

export const apiKeyFormSchema = z.object({
  apiKey: z.string().trim().min(1, "API-Key ist erforderlich"),
});
export type ApiKeyForm = z.infer<typeof apiKeyFormSchema>;
