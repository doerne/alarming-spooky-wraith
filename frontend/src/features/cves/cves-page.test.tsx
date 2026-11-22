import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CvesPage } from "./cves-page";

const TREND = {
  weeks: [{ weekStart: "2026-11-16", new: 2, closed: 1, openAtEnd: 5 }],
  openAtStart: 4,
  newTotal: 2,
  closedTotal: 1,
  untouchedNow: 3,
  inProgressNow: 2,
  openBySeverityNow: { kritisch: 1, hoch: 2, mittel: 1, niedrig: 1 },
};

function respondWith(body: unknown): Promise<Response> {
  return Promise.resolve(new Response(JSON.stringify(body), { status: 200 }));
}

function mockApi() {
  return vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = String(input);
    if (url.startsWith("/api/findings/trend")) return respondWith(TREND);
    if (url.startsWith("/api/cves"))
      return respondWith({ items: [], total: 0, unfilteredTotal: 0 });
    return respondWith({});
  });
}

function requestedUrls(fetchMock: ReturnType<typeof mockApi>): string[] {
  return fetchMock.mock.calls.map(([input]) => String(input));
}

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <CvesPage onSelectCve={vi.fn()} />
    </QueryClientProvider>,
  );
}

afterEach(() => vi.restoreAllMocks());

describe("CvesPage", () => {
  it("lädt die Tabelle zunächst nur mit offenen Funden", async () => {
    const fetchMock = mockApi();
    renderPage();

    await screen.findByTestId("cves-card-trend-open");

    expect(requestedUrls(fetchMock).some((url) => url.includes("/api/cves?status=offen"))).toBe(
      true,
    );
  });

  it("zeigt Kacheln und Diagramme, sobald der Trend geladen ist", async () => {
    mockApi();
    renderPage();

    expect(await screen.findByTestId("cves-card-trend-open")).toBeInTheDocument();
    expect(screen.getByTestId("cves-card-trend-chart")).toBeInTheDocument();
    expect(screen.getByTestId("cves-card-severity-chart")).toBeInTheDocument();
  });

  it("zeigt beim Laden des Trends keine Kacheln und stürzt nicht ab", () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => new Promise<Response>(() => {}));
    renderPage();

    expect(screen.queryByTestId("cves-card-trend-open")).not.toBeInTheDocument();
    expect(screen.getByTestId("cves-section-overview")).toBeInTheDocument();
  });

  it("meldet einen Fehler, wenn der Trend nicht geladen werden kann", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      if (String(input).startsWith("/api/findings/trend"))
        return Promise.resolve(new Response("{}", { status: 422 }));
      return respondWith({ items: [], total: 0, unfilteredTotal: 0 });
    });
    renderPage();

    expect(await screen.findByTestId("cves-error-trend")).toHaveTextContent(
      "Verlauf konnte nicht geladen werden.",
    );
  });

  it("lädt den Trend für den gewählten Zeitraum neu", async () => {
    const fetchMock = mockApi();
    renderPage();
    await screen.findByTestId("cves-card-trend-open");

    await userEvent.click(screen.getByTestId("cves-btn-trend-range-4"));

    expect(requestedUrls(fetchMock)).toContain("/api/findings/trend?weeks=4");
  });
});
