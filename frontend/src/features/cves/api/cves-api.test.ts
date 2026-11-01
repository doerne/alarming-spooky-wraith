import { describe, expect, it } from "vitest";

import { EMPTY_FILTERS } from "../model/filters";
import { buildFindingsQuery } from "./cves-api";

describe("buildFindingsQuery", () => {
  it("lässt leere Filter weg", () => {
    expect(buildFindingsQuery(EMPTY_FILTERS)).toBe("");
  });

  it("wiederholt Parameter für Mehrfachwerte und trimmt die Suche", () => {
    const query = buildFindingsQuery({
      ...EMPTY_FILTERS,
      severities: ["kritisch", "hoch"],
      ecosystems: ["none"],
      applicationId: 3,
      query: "  react ",
    });
    expect(query).toBe("?severity=kritisch&severity=hoch&ecosystem=none&application_id=3&q=react");
  });
});
