import { afterEach, describe, expect, it, vi } from "vitest";

import { EMPTY_CVE_FILTERS } from "../model/cve-filters";
import { applicationFindingsPath, listApplicationsOverview } from "./inventory-api";

describe("applicationFindingsPath", () => {
  it("hängt die Filter an die Anwendungs-ID an", () => {
    const path = applicationFindingsPath(4, {
      ...EMPTY_CVE_FILTERS,
      statuses: ["offen", "in_arbeit"],
      advisoryIds: ["CVE-2024-1"],
      componentNames: ["react"],
    });
    expect(path).toBe(
      "/api/cves?application_id=4&status=offen&status=in_arbeit&advisory_id=CVE-2024-1&component_name=react",
    );
  });
});

describe("listApplicationsOverview", () => {
  afterEach(() => vi.restoreAllMocks());

  it("lädt die Übersicht und lehnt ungültige Antworten ab", async () => {
    const fetchMock = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(new Response(JSON.stringify([{ id: 1 }]), { status: 200 }));
    await expect(listApplicationsOverview()).rejects.toThrow();
    expect(String(fetchMock.mock.calls[0]?.[0])).toBe("/api/applications/overview");
  });
});
