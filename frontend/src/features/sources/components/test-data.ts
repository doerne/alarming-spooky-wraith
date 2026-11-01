import type { Source } from "../model/types";

export function makeSource(overrides: Partial<Source> = {}): Source {
  return {
    key: "osv",
    name: "OSV.dev",
    homepageUrl: "https://osv.dev",
    description: "Open Source Vulnerabilities",
    kind: "package_query",
    scope: "package",
    apiKeyRequirement: "none",
    apiKeyHint: "",
    hasApiKey: false,
    enabled: true,
    status: "ready",
    lastRunAt: null,
    lastStatus: null,
    lastMessage: "",
    lastFindings: null,
    ...overrides,
  };
}
