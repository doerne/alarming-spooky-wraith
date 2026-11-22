import { describe, expect, it } from "vitest";

import { SBOM_NAME_MAX_LENGTH, sbomUploadSchema } from "./sbom-schema";

describe("sbomUploadSchema", () => {
  it("akzeptiert Name und Version und kürzt Leerzeichen", () => {
    expect(sbomUploadSchema.parse({ name: " backend ", label: "1.0" })).toEqual({
      name: "backend",
      label: "1.0",
    });
  });

  it.each(["", "   "])("verlangt einen Namen (%j)", (name) => {
    const result = sbomUploadSchema.safeParse({ name, label: "" });
    expect(result.success).toBe(false);
    expect(result.error?.issues[0]?.message).toBe("Name ist erforderlich");
  });

  it("begrenzt die Namenslänge", () => {
    const name = "x".repeat(SBOM_NAME_MAX_LENGTH + 1);
    expect(sbomUploadSchema.safeParse({ name, label: "" }).success).toBe(false);
  });
});
