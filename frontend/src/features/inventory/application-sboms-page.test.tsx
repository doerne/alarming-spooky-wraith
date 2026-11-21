import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApplicationSbomsPage } from "./application-sboms-page";
import { ARCHIVED_VERSION, SBOM } from "./components/sbom-fixtures";

const UPLOAD_RESULT = {
  sbomId: 3,
  version: SBOM.current,
  added: 5,
  removed: 2,
  kept: 400,
  unchecked: 318,
  skipped: 0,
};

function respond(body: unknown, status = 200): Promise<Response> {
  return Promise.resolve(new Response(JSON.stringify(body), { status }));
}

function mockApi(deleteStatus = 204) {
  return vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
    const path = String(input);
    if (init?.method === "POST") return respond(UPLOAD_RESULT, 201);
    if (init?.method === "DELETE") {
      return Promise.resolve(new Response(null, { status: deleteStatus }));
    }
    if (path.endsWith("/versions/7")) return respond(ARCHIVED_VERSION);
    if (path.endsWith("/versions")) return respond([ARCHIVED_VERSION]);
    return respond([SBOM]);
  });
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <ApplicationSbomsPage applicationId={1} />
    </QueryClientProvider>,
  );
}

function sbomFile(): File {
  const document = { bomFormat: "CycloneDX", metadata: { component: { name: "backend" } } };
  return new File([JSON.stringify(document)], "backend.cdx.json", { type: "application/json" });
}

afterEach(() => vi.restoreAllMocks());

describe("ApplicationSbomsPage", () => {
  it("zeigt nach dem Upload die Zusammenfassung", async () => {
    const fetchMock = mockApi();
    renderPage();

    await userEvent.click(await screen.findByTestId("inventory-btn-sbom-upload"));
    await userEvent.upload(screen.getByTestId("inventory-input-sbom-file"), sbomFile());
    await waitFor(() =>
      expect(screen.getByTestId("inventory-input-sbom-name")).toHaveValue("backend"),
    );
    await userEvent.click(screen.getByTestId("inventory-btn-sbom-submit"));

    expect(await screen.findByTestId("inventory-text-sbom-result")).toHaveTextContent(
      "5 hinzugefügt · 2 entfernt · 400 unverändert · 318 nicht geprüft",
    );
    expect(screen.getByTestId("inventory-text-sbom-result")).toHaveTextContent(
      "Neue Treffer erscheinen nach dem nächsten Abgleich.",
    );
    const post = fetchMock.mock.calls.find(([, init]) => init?.method === "POST");
    expect(String(post?.[0])).toBe("/api/applications/1/sboms/versions");
    expect(screen.queryByTestId("inventory-dialog-sbom-upload")).not.toBeInTheDocument();
  });

  it("öffnet den Verlauf und zeigt eine archivierte Version", async () => {
    mockApi();
    renderPage();

    await userEvent.click(await screen.findByTestId("inventory-btn-sbom-history-3"));
    await userEvent.click(await screen.findByTestId("inventory-btn-sbom-version-7"));

    expect(await screen.findByTestId("inventory-list-sbom-components")).toHaveTextContent(
      "openssl",
    );
  });

  it("löscht eine SBOM nach Bestätigung", async () => {
    const fetchMock = mockApi();
    renderPage();

    await userEvent.click(await screen.findByTestId("inventory-btn-sbom-delete-3"));
    await userEvent.click(screen.getByTestId("inventory-btn-sbom-delete-confirm"));

    await waitFor(() =>
      expect(screen.queryByTestId("inventory-dialog-sbom-delete")).not.toBeInTheDocument(),
    );
    const call = fetchMock.mock.calls.find(([, init]) => init?.method === "DELETE");
    expect(String(call?.[0])).toBe("/api/applications/1/sboms/3");
  });

  it("zeigt einen Fehler, wenn das Löschen scheitert", async () => {
    mockApi(500);
    renderPage();

    await userEvent.click(await screen.findByTestId("inventory-btn-sbom-delete-3"));
    await userEvent.click(screen.getByTestId("inventory-btn-sbom-delete-confirm"));

    expect(await screen.findByTestId("inventory-error-sbom-delete")).toBeInTheDocument();
  });

  it("meldet, wenn die SBOMs nicht geladen werden können", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => respond({ detail: "kaputt" }, 500));
    renderPage();

    expect(await screen.findByTestId("inventory-error-sboms-load")).toBeInTheDocument();
    expect(screen.queryByTestId("inventory-text-no-sboms")).not.toBeInTheDocument();
  });
});
