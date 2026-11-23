import type { ApplicationOverview } from "../model/overview";

export function overviewRow(overrides: Partial<ApplicationOverview> = {}): ApplicationOverview {
  return {
    id: 1,
    name: "Shop",
    description: "Online-Shop",
    openBySeverity: { kritisch: 2, hoch: 1, mittel: 0, niedrig: 0 },
    overdue: 1,
    componentCount: 412,
    latestSbomUploadAt: "2026-12-08T10:00:00Z",
    sbomStale: false,
    scanState: "current",
    inventoryChangedAt: null,
    githubRepository: "acme/shop",
    ...overrides,
  };
}
