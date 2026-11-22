import { describe, expect, it } from "vitest";

import {
  type ApplicationOverview,
  applicationOverviewSchema,
  DEFAULT_OVERVIEW_SORT,
  filterOverview,
  sbomAgeText,
  sortOverview,
  summarizeOverview,
} from "./overview";

const NOW = new Date("2026-12-10T10:00:00Z");

function row(overrides: Partial<ApplicationOverview> = {}): ApplicationOverview {
  return {
    id: 1,
    name: "app",
    description: "",
    openBySeverity: { kritisch: 0, hoch: 0, mittel: 0, niedrig: 0 },
    overdue: 0,
    componentCount: 0,
    latestSbomUploadAt: "2026-12-08T10:00:00Z",
    sbomStale: false,
    scanState: "current",
    inventoryChangedAt: null,
    githubRepository: null,
    ...overrides,
  };
}

function open(kritisch: number, hoch: number): ApplicationOverview["openBySeverity"] {
  return { kritisch, hoch, mittel: 0, niedrig: 0 };
}

const BURNING = row({ id: 1, name: "burning", openBySeverity: open(2, 0), overdue: 3 });
const STALE = row({
  id: 2,
  name: "stale",
  openBySeverity: open(0, 1),
  sbomStale: true,
  scanState: "changed_since_scan",
});
const EMPTY = row({
  id: 3,
  name: "empty",
  latestSbomUploadAt: null,
  sbomStale: true,
  scanState: "never_scanned",
});
const ROWS = [BURNING, STALE, EMPTY];

const names = (rows: ApplicationOverview[]) => rows.map((item) => item.name);

describe("summarizeOverview", () => {
  it("zählt Anwendungen je Kachel", () => {
    expect(summarizeOverview(ROWS)).toEqual({ critical: 1, overdue: 1, sbom: 2, unscanned: 2 });
  });
});

describe("filterOverview", () => {
  it("zeigt nur die Anwendungen der Kachel", () => {
    expect(names(filterOverview(ROWS, "sbom"))).toEqual(["stale", "empty"]);
  });

  it("zeigt ohne Kachel alle", () => {
    expect(filterOverview(ROWS, null)).toHaveLength(3);
  });
});

describe("sortOverview", () => {
  it("stellt standardmäßig die kritischsten nach vorn", () => {
    const a = row({ name: "a", openBySeverity: open(0, 5) });
    const b = row({ name: "b", openBySeverity: open(2, 0) });
    const c = row({ name: "c", openBySeverity: open(2, 0), overdue: 1 });
    expect(names(sortOverview([a, b, c], DEFAULT_OVERVIEW_SORT))).toEqual(["c", "b", "a"]);
  });

  it("entscheidet bei Gleichstand nach Name aufsteigend, in beide Richtungen", () => {
    const beta = row({ name: "beta" });
    const alpha = row({ name: "alpha" });
    expect(names(sortOverview([beta, alpha], { key: "overdue", direction: "desc" }))).toEqual([
      "alpha",
      "beta",
    ]);
    expect(names(sortOverview([beta, alpha], { key: "overdue", direction: "asc" }))).toEqual([
      "alpha",
      "beta",
    ]);
  });

  it("stellt fehlende und alte SBOMs absteigend nach vorn", () => {
    const newest = row({ name: "newest", latestSbomUploadAt: "2026-12-09T00:00:00Z" });
    const oldest = row({ name: "oldest", latestSbomUploadAt: "2026-10-01T00:00:00Z" });
    const none = row({ name: "none", latestSbomUploadAt: null });
    const sorted = sortOverview([newest, oldest, none], { key: "sbom", direction: "desc" });
    expect(names(sorted)).toEqual(["none", "oldest", "newest"]);
  });

  it("stellt nie gescannte, dann ältere Änderungen absteigend nach vorn", () => {
    const current = row({ name: "current" });
    const recent = row({
      name: "recent",
      scanState: "changed_since_scan",
      inventoryChangedAt: "2026-12-09T00:00:00Z",
    });
    const older = row({
      name: "older",
      scanState: "changed_since_scan",
      inventoryChangedAt: "2026-12-01T00:00:00Z",
    });
    const never = row({ name: "never", scanState: "never_scanned" });
    const sorted = sortOverview([current, recent, older, never], {
      key: "scan",
      direction: "desc",
    });
    expect(names(sorted)).toEqual(["never", "older", "recent", "current"]);
  });
});

describe("sortOverview je Spalte", () => {
  const small = row({ name: "b", componentCount: 1, githubRepository: null });
  const large = row({ name: "a", componentCount: 9, githubRepository: "acme/z" });
  it.each([
    ["name", ["a", "b"]],
    ["components", ["b", "a"]],
    ["github", ["b", "a"]],
  ] as const)("sortiert %s aufsteigend", (key, expected) => {
    expect(names(sortOverview([large, small], { key, direction: "asc" }))).toEqual(expected);
  });
});

describe("sbomAgeText", () => {
  it("nennt das Alter in vollen Tagen", () => {
    expect(sbomAgeText("2026-12-10T08:00:00Z", NOW)).toBe("heute");
    expect(sbomAgeText("2026-12-09T08:00:00Z", NOW)).toBe("vor 1 Tag");
    expect(sbomAgeText("2026-12-05T08:00:00Z", NOW)).toBe("vor 5 Tagen");
  });
});

describe("applicationOverviewSchema", () => {
  it("liest die Antwort des Backends", () => {
    const parsed = applicationOverviewSchema.parse({
      id: 1,
      name: "Shop",
      description: "",
      openBySeverity: { kritisch: 0, hoch: 0, mittel: 0, niedrig: 0 },
      overdue: 0,
      componentCount: 1,
      latestSbomUploadAt: null,
      sbomStale: true,
      scanState: "never_scanned",
      inventoryChangedAt: "2026-11-22T10:00:00Z",
      githubRepository: null,
    });
    expect(parsed.scanState).toBe("never_scanned");
  });

  it("lehnt ungültige Zeitpunkte ab", () => {
    const invalid = { ...row(), latestSbomUploadAt: "gestern" };
    expect(applicationOverviewSchema.safeParse(invalid).success).toBe(false);
  });
});
