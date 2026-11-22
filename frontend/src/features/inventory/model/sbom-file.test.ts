import { describe, expect, it } from "vitest";

import { readSbomFile, SbomFileError } from "./sbom-file";

function fileOf(content: string, name = "backend-image.cdx.json"): File {
  return new File([content], name, { type: "application/json" });
}

describe("readSbomFile", () => {
  it("liest Name und Version aus metadata.component", async () => {
    const document = {
      bomFormat: "CycloneDX",
      metadata: { component: { name: "backend", version: "1.4.0" } },
      components: [],
    };
    const result = await readSbomFile(fileOf(JSON.stringify(document)));
    expect(result.suggestedName).toBe("backend");
    expect(result.suggestedLabel).toBe("1.4.0");
    expect(result.document).toEqual(document);
  });

  it("nimmt den Dateinamen, wenn metadata fehlt", async () => {
    const result = await readSbomFile(fileOf(JSON.stringify({ bomFormat: "CycloneDX" })));
    expect(result.suggestedName).toBe("backend-image");
    expect(result.suggestedLabel).toBe("");
  });

  it("meldet Dateien, die kein JSON sind", async () => {
    await expect(readSbomFile(fileOf("kein json"))).rejects.toThrow(
      new SbomFileError("Die Datei ist kein gültiges JSON."),
    );
  });

  it("meldet JSON, das keine CycloneDX-SBOM ist", async () => {
    const spdx = JSON.stringify({ spdxVersion: "SPDX-2.3" });
    await expect(readSbomFile(fileOf(spdx, "sbom.spdx.json"))).rejects.toThrow(
      new SbomFileError("Die Datei ist keine CycloneDX-SBOM."),
    );
  });

  it("meldet ein JSON-Array als keine CycloneDX-SBOM", async () => {
    await expect(readSbomFile(fileOf("[]"))).rejects.toBeInstanceOf(SbomFileError);
  });
});
