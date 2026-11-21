export class SbomFileError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "SbomFileError";
  }
}

export interface SbomFile {
  document: Record<string, unknown>;
  suggestedName: string;
  suggestedLabel: string;
}

const FILE_EXTENSIONS = /(\.cdx)?\.json$/i;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function parseJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    throw new SbomFileError("Die Datei ist kein gültiges JSON.");
  }
}

function rootComponent(document: Record<string, unknown>): Record<string, unknown> {
  const metadata = isRecord(document.metadata) ? document.metadata : {};
  return isRecord(metadata.component) ? metadata.component : {};
}

function textOr(value: unknown, fallback: string): string {
  return typeof value === "string" && value.length > 0 ? value : fallback;
}

/** Liest eine CycloneDX-JSON-Datei im Browser und schlägt Name und Version vor. */
export async function readSbomFile(file: File): Promise<SbomFile> {
  const parsed = parseJson(await file.text());
  if (!isRecord(parsed) || parsed.bomFormat !== "CycloneDX") {
    throw new SbomFileError("Die Datei ist keine CycloneDX-SBOM.");
  }
  const root = rootComponent(parsed);
  return {
    document: parsed,
    suggestedName: textOr(root.name, file.name.replace(FILE_EXTENSIONS, "")),
    suggestedLabel: textOr(root.version, ""),
  };
}
