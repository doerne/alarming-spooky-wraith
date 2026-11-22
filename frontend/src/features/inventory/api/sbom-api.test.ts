import { afterEach, describe, expect, it, vi } from "vitest";

import { deleteSbom, getSbomVersion, uploadSbomVersion } from "./sbom-api";

function mockFetch(status: number, body: unknown) {
  const fetchMock = vi
    .fn()
    .mockResolvedValue(new Response(status === 204 ? null : JSON.stringify(body), { status }));
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("sbom-api", () => {
  it("lädt eine SBOM-Version als JSON hoch", async () => {
    const fetchMock = mockFetch(201, { sbomId: 3 });
    const body = { name: "backend", label: "1.0", document: { bomFormat: "CycloneDX" } };

    const result = await uploadSbomVersion(1, body);

    expect(result).toEqual({ sbomId: 3 });
    const [path, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(path).toBe("/api/applications/1/sboms/versions");
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual(body);
  });

  it("holt eine Version mit Komponenten", async () => {
    const fetchMock = mockFetch(200, { id: 7, components: [] });
    await getSbomVersion(1, 3, 7);
    expect(fetchMock.mock.calls[0]?.[0]).toBe("/api/applications/1/sboms/3/versions/7");
  });

  it("löscht eine SBOM", async () => {
    const fetchMock = mockFetch(204, null);
    await deleteSbom(1, 3);
    const [path, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(path).toBe("/api/applications/1/sboms/3");
    expect(init.method).toBe("DELETE");
  });
});
