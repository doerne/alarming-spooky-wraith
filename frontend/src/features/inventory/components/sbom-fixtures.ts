import type { SbomSummary, SbomVersionDetail } from "../model/sbom-types";

export const SBOM: SbomSummary = {
  id: 3,
  name: "backend-image",
  versionCount: 2,
  current: {
    id: 8,
    label: "v1.4.0",
    uploadedAt: "2026-11-21T09:30:00Z",
    isCurrent: true,
    componentCount: 412,
    uncheckedCount: 318,
  },
};

export const ARCHIVED_VERSION: SbomVersionDetail = {
  id: 7,
  label: "v1.3.0",
  uploadedAt: "2026-11-01T09:30:00Z",
  isCurrent: false,
  componentCount: 2,
  uncheckedCount: 1,
  components: [
    {
      name: "react",
      version: "18.2.0",
      category: "library",
      ecosystem: "npm",
      direct: true,
      purl: "pkg:npm/react@18.2.0",
      checked: true,
    },
    {
      name: "openssl",
      version: "3.0.11",
      category: "library",
      ecosystem: null,
      direct: false,
      purl: "pkg:deb/debian/openssl@3.0.11",
      checked: false,
    },
  ],
};
