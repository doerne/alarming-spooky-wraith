import { describe, expect, it } from "vitest";

import { EMPTY_FILTERS } from "../model/filters";
import { buildFindingsQuery } from "./cves-api";

describe("buildFindingsQuery", () => {
  it("lässt leere Filter weg", () => {
    expect(buildFindingsQuery(EMPTY_FILTERS)).toBe("");
  });

  it("wiederholt Parameter für Mehrfachwerte und reicht Advisory-IDs und Komponenten weiter", () => {
    const query = buildFindingsQuery({
      ...EMPTY_FILTERS,
      severities: ["kritisch", "hoch"],
      ecosystems: ["none"],
      applicationIds: [3, 4],
      advisoryIds: ["CVE-2024-1"],
      componentNames: ["react", "vue"],
    });
    expect(query).toBe(
      "?severity=kritisch&severity=hoch&ecosystem=none&application=3&application=4&advisory_id=CVE-2024-1&component_name=react&component_name=vue",
    );
  });
});
