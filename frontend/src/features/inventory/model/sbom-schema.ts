import { z } from "zod";

export const SBOM_NAME_MAX_LENGTH = 100;
export const SBOM_LABEL_MAX_LENGTH = 100;

export const sbomUploadSchema = z.object({
  name: z
    .string()
    .trim()
    .min(1, "Name ist erforderlich")
    .max(SBOM_NAME_MAX_LENGTH, `Höchstens ${SBOM_NAME_MAX_LENGTH} Zeichen`),
  label: z.string().max(SBOM_LABEL_MAX_LENGTH, `Höchstens ${SBOM_LABEL_MAX_LENGTH} Zeichen`),
});
export type SbomUploadInput = z.infer<typeof sbomUploadSchema>;
