import { z } from "zod";

export const categorySchema = z.enum(["language", "framework", "library", "service"]);
export const ecosystemSchema = z.enum([
  "npm",
  "PyPI",
  "Go",
  "crates.io",
  "RubyGems",
  "Packagist",
  "Maven",
  "NuGet",
  "Hackage",
  "CRAN",
  "opam",
]);

export const componentSchema = z.object({
  name: z.string().min(1, "Name ist erforderlich"),
  version: z.string().min(1, "Version ist erforderlich"),
  category: categorySchema,
  ecosystem: ecosystemSchema.nullable(),
  direct: z.boolean(),
});
export type ComponentInput = z.infer<typeof componentSchema>;

export const applicationSchema = z.object({
  name: z.string().min(1, "Name ist erforderlich"),
});
export type ApplicationInput = z.infer<typeof applicationSchema>;
