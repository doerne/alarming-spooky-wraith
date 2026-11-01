import { describe, expect, it } from "vitest";

import { EMPTY_FILTERS } from "../model/filters";
import { buildFindingsQuery } from "./cves-api";

describe("buildFindingsQuery", () => {
  it("lässt leere Filter weg", () => {
    expect(buildFindingsQuery(EMPTY_FILTERS)).toBe("");
  });

  it("wiederholt Parameter für Mehrfachwerte und trimmt die Suchfelder", () => {
    const query = buildFindingsQuery({
      ...EMPTY_FILTERS,
      severities: ["kritisch", "hoch"],
      ecosystems: ["none"],
      applicationIds: [3, 4],
      advisoryQuery: " xss ",
      componentQuery: "react",
    });
    expect(query).toBe(
      "?severity=kritisch&severity=hoch&ecosystem=none&application=3&application=4&advisory=xss&component=react",
    );
  });
});
