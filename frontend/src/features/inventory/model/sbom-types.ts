export interface SbomVersionSummary {
  id: number;
  label: string;
  uploadedAt: string;
  isCurrent: boolean;
  componentCount: number;
  uncheckedCount: number;
}

export interface SbomEntry {
  name: string;
  version: string;
  category: string;
  ecosystem: string | null;
  direct: boolean;
  purl: string | null;
  checked: boolean;
}

export interface SbomVersionDetail extends SbomVersionSummary {
  components: SbomEntry[];
}

export interface SbomSummary {
  id: number;
  name: string;
  versionCount: number;
  current: SbomVersionSummary | null;
}

export interface SbomUploadResult {
  sbomId: number;
  version: SbomVersionSummary;
  added: number;
  removed: number;
  kept: number;
  unchecked: number;
  skipped: number;
}

export interface SbomUploadBody {
  name: string;
  label: string | null;
  document: Record<string, unknown>;
}
