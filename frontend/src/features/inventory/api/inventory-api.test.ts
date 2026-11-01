import { describe, expect, it } from "vitest";

import { EMPTY_CVE_FILTERS } from "../model/cve-filters";
import { applicationFindingsPath } from "./inventory-api";

describe("applicationFindingsPath", () => {
  it("hängt die Filter an die Anwendungs-ID an", () => {
    const path = applicationFindingsPath(4, {
      ...EMPTY_CVE_FILTERS,
      statuses: ["offen", "in_arbeit"],
      query: " xss ",
    });
    expect(path).toBe("/api/cves?application_id=4&status=offen&status=in_arbeit&q=xss");
  });
});
