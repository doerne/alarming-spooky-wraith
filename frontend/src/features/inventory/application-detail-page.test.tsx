import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApplicationDetailPage } from "./application-detail-page";
import { SBOM } from "./components/sbom-fixtures";

const BUSY_MESSAGE = "Während eines Scans oder GitHub-Abgleichs kann nicht gelöscht werden.";

const COMPONENT = {
  id: 5,
  applicationId: 1,
  name: "react",
  version: "18.2.0",
  category: "library",
  ecosystem: "npm",
  direct: true,
  sbomId: null,
  checked: true,
};

const APPLICATION = {
  id: 1,
  name: "Shop",
  description: "",
  components: [COMPONENT],
  githubRepository: null,
  autoIssueMinLevel: null,
  githubSyncedAt: null,
  githubSyncMessage: "",
  inventoryChangedAt: null,
};

function respond(body: unknown, status = 200): Promise<Response> {
  return Promise.resolve(new Response(JSON.stringify(body), { status }));
}

function deleteResponse(status: number): Promise<Response> {
  if (status === 204) return Promise.resolve(new Response(null, { status }));
  return respond({ detail: BUSY_MESSAGE }, status);
}

function mockApi(deleteStatus = 204) {
  return vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
    const path = String(input);
    if (init?.method === "DELETE") return deleteResponse(deleteStatus);
    if (path === "/api/applications/1") return respond(APPLICATION);
    if (path === "/api/applications/1/sboms") return respond([SBOM]);
    if (path.startsWith("/api/cves")) return respond({ items: [], total: 0, unfilteredTotal: 4 });
    return respond({});
  });
}

function renderPage(onBack = vi.fn()) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <ApplicationDetailPage applicationId={1} onBack={onBack} onSelectCve={vi.fn()} />
    </QueryClientProvider>,
  );
  return onBack;
}

async function confirmDeletion() {
  await userEvent.click(await screen.findByTestId("inventory-btn-delete-app"));
  await userEvent.click(screen.getByTestId("inventory-btn-confirm-delete-app"));
}

afterEach(() => vi.restoreAllMocks());

describe("ApplicationDetailPage – Anwendung löschen", () => {
  it("nennt im Dialog die Anzahl der betroffenen Daten", async () => {
    mockApi();
    renderPage();

    await userEvent.click(await screen.findByTestId("inventory-btn-delete-app"));

    await waitFor(() =>
      expect(screen.getByTestId("inventory-dialog-delete-app")).toHaveTextContent(
        "Shop mit 1 Komponenten, 1 SBOMs und 4 Funden endgültig löschen?",
      ),
    );
  });

  it("löscht nach Bestätigung und kehrt zur Übersicht zurück", async () => {
    const fetchMock = mockApi();
    const onBack = renderPage();

    await confirmDeletion();

    await waitFor(() => expect(onBack).toHaveBeenCalledOnce());
    const call = fetchMock.mock.calls.find(([, init]) => init?.method === "DELETE");
    expect(String(call?.[0])).toBe("/api/applications/1");
  });

  it("lässt den Dialog bei 409 offen und zeigt die Meldung", async () => {
    mockApi(409);
    const onBack = renderPage();

    await confirmDeletion();

    expect(await screen.findByTestId("inventory-error-delete-app")).toHaveTextContent(BUSY_MESSAGE);
    expect(screen.getByTestId("inventory-dialog-delete-app")).toBeInTheDocument();
    expect(onBack).not.toHaveBeenCalled();
  });
});
