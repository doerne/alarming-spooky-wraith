import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApplicationCvesPage } from "./application-cves-page";

const FINDING = {
  advisoryId: "CVE-2024-1",
  cveId: "CVE-2024-1",
  title: "XSS",
  componentId: 1,
  componentName: "react",
  componentVersion: "18.2.0",
  ecosystem: "npm",
  riskScore: 98,
  riskLevel: "kritisch",
  fixVersion: null,
  status: "offen",
};

const TREND = {
  weeks: [{ weekStart: "2026-11-16", new: 2, closed: 1, openAtEnd: 5 }],
  openAtStart: 4,
  newTotal: 2,
  closedTotal: 1,
  untouchedNow: 3,
  inProgressNow: 2,
  openBySeverityNow: { kritisch: 1, hoch: 2, mittel: 1, niedrig: 1 },
};

function mockFindings(byApp: Record<string, (typeof FINDING)[]>) {
  return vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = new URL(String(input), "http://localhost");
    if (url.pathname === "/api/findings/trend") {
      return Promise.resolve(new Response(JSON.stringify(TREND), { status: 200 }));
    }
    const all = byApp[url.searchParams.get("application_id") ?? ""] ?? [];
    const severities = url.searchParams.getAll("severity");
    const items = severities.length ? all.filter((f) => severities.includes(f.riskLevel)) : all;
    const body = { items, total: items.length, unfilteredTotal: all.length };
    return Promise.resolve(new Response(JSON.stringify(body), { status: 200 }));
  });
}

function renderPage(applicationId: number) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const view = render(
    <QueryClientProvider client={client}>
      <ApplicationCvesPage applicationId={applicationId} onSelectCve={vi.fn()} />
    </QueryClientProvider>,
  );
  return { ...view, client };
}

afterEach(() => vi.restoreAllMocks());

describe("ApplicationCvesPage", () => {
  it("zeigt den Trend der Anwendung und lädt die Funde zunächst nur offen", async () => {
    const fetchMock = mockFindings({ "7": [FINDING] });
    renderPage(7);

    expect(await screen.findByTestId("inventory-card-trend-open")).toBeInTheDocument();
    const urls = fetchMock.mock.calls.map(([input]) => String(input));
    expect(
      urls.some((url) => url.includes("/api/findings/trend") && url.includes("applicationId=7")),
    ).toBe(true);
    expect(
      urls.some((url) => url.includes("application_id=7") && url.includes("status=offen")),
    ).toBe(true);
  });

  it("zeigt einen Fehlerhinweis, wenn der Trend nicht lädt", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const status = String(input).startsWith("/api/findings/trend") ? 500 : 200;
      const body = status === 500 ? {} : { items: [], total: 0, unfilteredTotal: 0 };
      return Promise.resolve(new Response(JSON.stringify(body), { status }));
    });
    renderPage(1);

    expect(await screen.findByTestId("inventory-error-trend")).toHaveAttribute("role", "alert");
    expect(screen.queryByTestId("inventory-card-trend-open")).not.toBeInTheDocument();
  });

  it("blendet beim Laden keinen Hinweis ein", () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => new Promise<Response>(() => {}));
    renderPage(1);

    expect(screen.queryByTestId("inventory-text-no-cves")).not.toBeInTheDocument();
  });

  it("zeigt N von M und setzt zurück", async () => {
    mockFindings({ "1": [FINDING] });
    renderPage(1);

    expect(await screen.findByTestId("inventory-text-filter-summary")).toHaveTextContent("1 von 1");
    // Startfilter "offen" ist aktiv, Zurücksetzen hebt ihn auf.
    await userEvent.click(screen.getByTestId("inventory-btn-reset-filters"));
    expect(screen.getByTestId("inventory-btn-reset-filters")).toBeDisabled();
  });

  it("zeigt ohne Funde nur den Hinweis, keine Filter", async () => {
    mockFindings({});
    renderPage(1);

    expect(await screen.findByTestId("inventory-text-no-cves")).toBeInTheDocument();
    expect(screen.queryByTestId("inventory-list-cves")).not.toBeInTheDocument();
  });

  it("behält Tabelle und Kopf-Filter, wenn Filter nichts finden", async () => {
    mockFindings({ "1": [FINDING] });
    renderPage(1);

    await screen.findByTestId("inventory-item-cve-CVE-2024-1-1");
    await userEvent.click(screen.getByTestId("inventory-select-severity"));
    await userEvent.click(screen.getByTestId("inventory-checkbox-severity-niedrig"));

    expect(await screen.findByTestId("inventory-text-no-results")).toBeInTheDocument();
    expect(screen.getByTestId("inventory-list-cves")).toBeInTheDocument();
    expect(screen.getByTestId("inventory-text-filter-summary")).toHaveTextContent("0 von 1");
  });

  it("zeigt nach Anwendungswechsel keine Funde der vorherigen Anwendung", async () => {
    mockFindings({ "1": [FINDING], "2": [] });
    const { rerender, client } = renderPage(1);
    await screen.findByTestId("inventory-item-cve-CVE-2024-1-1");

    rerender(
      <QueryClientProvider client={client}>
        <ApplicationCvesPage applicationId={2} onSelectCve={vi.fn()} />
      </QueryClientProvider>,
    );

    expect(screen.queryByTestId("inventory-item-cve-CVE-2024-1-1")).not.toBeInTheDocument();
    expect(await screen.findByTestId("inventory-text-no-cves")).toBeInTheDocument();
  });
});
