import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { overviewRow } from "./components/overview-fixtures";
import { InventoryPage } from "./inventory-page";
import type { ApplicationOverview } from "./model/overview";

const BURNING = overviewRow({ id: 1, name: "Shop" });
const STALE = overviewRow({
  id: 2,
  name: "Blog",
  openBySeverity: { kritisch: 0, hoch: 0, mittel: 0, niedrig: 0 },
  overdue: 0,
  latestSbomUploadAt: null,
  sbomStale: true,
});

const DETAIL = {
  id: 1,
  name: "Shop",
  description: "",
  components: [],
  githubRepository: null,
  autoIssueMinLevel: null,
  githubSyncedAt: null,
  githubSyncMessage: "",
  inventoryChangedAt: null,
};

const IDLE_SCAN = {
  running: false,
  startedAt: null,
  finishedAt: null,
  componentsScanned: null,
  findingsFound: null,
  error: null,
  lastRun: null,
  lastUsableRun: null,
  steps: [],
};

const CREATED = { id: 1, name: "Shop", description: "" };

function routeOf(path: string, rows: ApplicationOverview[]): unknown {
  const routes: Record<string, unknown> = {
    "/api/applications/overview": rows,
    "/api/applications/1": DETAIL,
    "/api/applications/1/sboms": [],
    "/api/ingest/status": IDLE_SCAN,
  };
  if (path in routes) return routes[path];
  return path.startsWith("/api/cves") ? { items: [], total: 0, unfilteredTotal: 0 } : {};
}

function mockApi(rows: ApplicationOverview[], overviewStatus = 200) {
  return vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
    const path = String(input);
    if (init?.method === "POST") {
      return Promise.resolve(new Response(JSON.stringify(CREATED), { status: 201 }));
    }
    const status = path === "/api/applications/overview" ? overviewStatus : 200;
    return Promise.resolve(new Response(JSON.stringify(routeOf(path, rows)), { status }));
  });
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={client}>
      <InventoryPage onSelectCve={vi.fn()} />
    </QueryClientProvider>,
  );
}

afterEach(() => vi.restoreAllMocks());

describe("InventoryPage", () => {
  it("zeigt die Summen über alle Anwendungen", async () => {
    mockApi([BURNING, STALE]);
    renderPage();
    expect(await screen.findByTestId("inventory-text-tile-critical")).toHaveTextContent("1");
    expect(screen.getByTestId("inventory-text-tile-sbom")).toHaveTextContent("1");
  });

  it("filtert per Kachel und zeigt nach erneutem Klick wieder alle", async () => {
    mockApi([BURNING, STALE]);
    renderPage();
    await userEvent.click(await screen.findByTestId("inventory-btn-tile-sbom"));
    expect(screen.queryByTestId("inventory-item-app-1")).toBeNull();
    expect(screen.getByTestId("inventory-item-app-2")).toBeInTheDocument();

    await userEvent.click(screen.getByTestId("inventory-btn-tile-sbom"));
    expect(screen.getByTestId("inventory-item-app-1")).toBeInTheDocument();
  });

  it("meldet einen leeren Filter und setzt ihn zurück", async () => {
    mockApi([STALE]);
    renderPage();
    await userEvent.click(await screen.findByTestId("inventory-btn-tile-critical"));
    expect(screen.getByTestId("inventory-text-filter-empty")).toBeInTheDocument();

    await userEvent.click(screen.getByTestId("inventory-btn-reset-filter"));
    expect(screen.getByTestId("inventory-item-app-2")).toBeInTheDocument();
  });

  it("zeigt einen Hinweis ohne Anwendungen", async () => {
    mockApi([]);
    renderPage();
    expect(await screen.findByTestId("inventory-text-empty")).toBeInTheDocument();
  });

  it("öffnet die Detailansicht per Klick auf die Zeile", async () => {
    mockApi([BURNING]);
    renderPage();
    await userEvent.click(await screen.findByTestId("inventory-item-app-1"));
    expect(await screen.findByTestId("inventory-section-detail")).toBeInTheDocument();
  });

  it("öffnet den Dialog zum Anlegen", async () => {
    mockApi([]);
    renderPage();
    await userEvent.click(await screen.findByTestId("inventory-btn-open-create-app"));
    expect(screen.getByTestId("inventory-dialog-create-app")).toBeInTheDocument();
  });

  it("legt eine Anwendung an und öffnet sie", async () => {
    const fetchMock = mockApi([]);
    renderPage();
    await userEvent.click(await screen.findByTestId("inventory-btn-open-create-app"));
    await userEvent.type(screen.getByTestId("inventory-input-app-name"), "Shop");
    await userEvent.click(screen.getByTestId("inventory-btn-create-app"));

    expect(await screen.findByTestId("inventory-section-detail")).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.queryByTestId("inventory-dialog-create-app")).not.toBeInTheDocument(),
    );
    const post = fetchMock.mock.calls.find(([, init]) => init?.method === "POST");
    expect(String(post?.[0])).toBe("/api/applications");
  });

  it("meldet, wenn die Übersicht nicht geladen werden kann", async () => {
    mockApi([], 500);
    renderPage();
    expect(await screen.findByTestId("inventory-error-overview")).toBeInTheDocument();
  });

  it("zeigt den Stand des letzten Scans", async () => {
    mockApi([]);
    renderPage();
    expect(await screen.findByTestId("inventory-text-scan-freshness")).toBeInTheDocument();
  });
});
