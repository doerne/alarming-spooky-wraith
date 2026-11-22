import { afterEach, describe, expect, it, vi } from "vitest";

import { fetchRemediationKpis } from "./remediation-kpis";

const payload = {
  deadlines: {
    overdue: 1,
    dueSoon: 2,
    overdueBySeverity: { kritisch: 1, hoch: 0, mittel: 0, niedrig: 0 },
    nextDueAt: null,
  },
  updates: { targets: [], fixableOpen: 0, openTotal: 0, morePackages: 0 },
};

function mockFetch() {
  const fetchMock = vi.fn<(url: string) => Promise<Response>>(
    async () => new Response(JSON.stringify(payload)),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => vi.unstubAllGlobals());

describe("fetchRemediationKpis", () => {
  it("ruft ohne Anwendung die globale URL auf", async () => {
    const fetchMock = mockFetch();

    const kpis = await fetchRemediationKpis({});

    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/findings/kpis");
    expect(kpis.deadlines.overdue).toBe(1);
  });

  it("hängt applicationId an", async () => {
    const fetchMock = mockFetch();

    await fetchRemediationKpis({ applicationId: 7 });

    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/findings/kpis?applicationId=7");
  });

  it("lehnt ungültige Antworten ab", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response(JSON.stringify({ deadlines: {} }))),
    );

    await expect(fetchRemediationKpis({})).rejects.toThrow();
  });
});
