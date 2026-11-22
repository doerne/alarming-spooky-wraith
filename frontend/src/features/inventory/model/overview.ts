import { z } from "zod";

export const OVERVIEW_SEVERITIES = ["kritisch", "hoch", "mittel", "niedrig"] as const;
export type OverviewSeverity = (typeof OVERVIEW_SEVERITIES)[number];

export const SCAN_STATES = ["current", "changed_since_scan", "never_scanned"] as const;
export type ScanState = (typeof SCAN_STATES)[number];

export const applicationOverviewSchema = z.object({
  id: z.number(),
  name: z.string(),
  description: z.string(),
  openBySeverity: z.object({
    kritisch: z.number(),
    hoch: z.number(),
    mittel: z.number(),
    niedrig: z.number(),
  }),
  overdue: z.number(),
  componentCount: z.number(),
  latestSbomUploadAt: z.iso.datetime({ offset: true }).nullable(),
  sbomStale: z.boolean(),
  scanState: z.enum(SCAN_STATES),
  inventoryChangedAt: z.iso.datetime({ offset: true }).nullable(),
  githubRepository: z.string().nullable(),
});
export type ApplicationOverview = z.infer<typeof applicationOverviewSchema>;

export const TILE_KEYS = ["critical", "overdue", "sbom", "unscanned"] as const;
export type TileKey = (typeof TILE_KEYS)[number];

const TILE_MATCHERS: Record<TileKey, (row: ApplicationOverview) => boolean> = {
  critical: (row) => row.openBySeverity.kritisch > 0,
  overdue: (row) => row.overdue > 0,
  sbom: (row) => row.sbomStale,
  unscanned: (row) => row.scanState !== "current",
};

export function matchesTile(row: ApplicationOverview, tile: TileKey): boolean {
  return TILE_MATCHERS[tile](row);
}

export function summarizeOverview(rows: ApplicationOverview[]): Record<TileKey, number> {
  const counts = TILE_KEYS.map((tile) => [
    tile,
    rows.filter((row) => matchesTile(row, tile)).length,
  ]);
  return Object.fromEntries(counts) as Record<TileKey, number>;
}

export function filterOverview(
  rows: ApplicationOverview[],
  tile: TileKey | null,
): ApplicationOverview[] {
  return tile === null ? rows : rows.filter((row) => matchesTile(row, tile));
}

export type SortKey = "name" | "open" | "overdue" | "components" | "sbom" | "scan" | "github";
export type SortDirection = "asc" | "desc";
export interface OverviewSort {
  key: SortKey;
  direction: SortDirection;
}
export const DEFAULT_OVERVIEW_SORT: OverviewSort = { key: "open", direction: "desc" };

type Comparator = (left: ApplicationOverview, right: ApplicationOverview) => number;

/** Alter in Millisekunden; fehlende Werte gelten als ältester Stand. */
function ageOf(iso: string | null): number {
  return iso === null ? Number.POSITIVE_INFINITY : -new Date(iso).getTime();
}

function compareNumbers(left: number, right: number): number {
  if (left === right) return 0;
  return left < right ? -1 : 1;
}

/** Je schlechter der Scan-Zustand, desto höher der Rang. */
const SCAN_RANK: Record<ScanState, number> = {
  current: 0,
  changed_since_scan: 1,
  never_scanned: 2,
};

function compareOpen(left: ApplicationOverview, right: ApplicationOverview): number {
  for (const severity of OVERVIEW_SEVERITIES) {
    const result = compareNumbers(left.openBySeverity[severity], right.openBySeverity[severity]);
    if (result !== 0) return result;
  }
  return compareNumbers(left.overdue, right.overdue);
}

function compareScan(left: ApplicationOverview, right: ApplicationOverview): number {
  const rank = compareNumbers(SCAN_RANK[left.scanState], SCAN_RANK[right.scanState]);
  if (rank !== 0) return rank;
  return compareNumbers(ageOf(left.inventoryChangedAt), ageOf(right.inventoryChangedAt));
}

/** Aufsteigende Vergleiche; „absteigend“ dreht sie um. */
const COMPARATORS: Record<SortKey, Comparator> = {
  name: (left, right) => left.name.localeCompare(right.name),
  open: compareOpen,
  overdue: (left, right) => compareNumbers(left.overdue, right.overdue),
  components: (left, right) => compareNumbers(left.componentCount, right.componentCount),
  sbom: (left, right) =>
    compareNumbers(ageOf(left.latestSbomUploadAt), ageOf(right.latestSbomUploadAt)),
  scan: compareScan,
  github: (left, right) =>
    (left.githubRepository ?? "").localeCompare(right.githubRepository ?? ""),
};

export function sortOverview(
  rows: ApplicationOverview[],
  sort: OverviewSort,
): ApplicationOverview[] {
  const compare = COMPARATORS[sort.key];
  const sign = sort.direction === "asc" ? 1 : -1;
  // Bei Gleichstand immer nach Name aufsteigend, damit die Reihenfolge stabil bleibt.
  return [...rows].sort(
    (left, right) => sign * compare(left, right) || left.name.localeCompare(right.name),
  );
}

const DAY_MS = 24 * 60 * 60 * 1000;

export function sbomAgeText(isoUploadedAt: string, now: Date): string {
  const days = Math.floor((now.getTime() - new Date(isoUploadedAt).getTime()) / DAY_MS);
  if (days <= 0) return "heute";
  return days === 1 ? "vor 1 Tag" : `vor ${days} Tagen`;
}
