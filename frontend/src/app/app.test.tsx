import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./app";
import { Providers } from "./providers";

function renderApp() {
  return render(
    <Providers>
      <App />
    </Providers>,
  );
}

const FINDING = {
  advisoryId: "CVE-2024-1",
  cveId: "CVE-2024-1",
  title: "XSS",
  applicationId: 1,
  applicationName: "Shop",
  componentId: 1,
  componentName: "react",
  componentVersion: "18.2.0",
  ecosystem: "npm",
  riskScore: 98,
  riskLevel: "kritisch",
  fixVersion: "18.2.1",
  status: "offen",
};

const DETAIL = {
  advisoryId: "CVE-2024-1",
  cveId: "CVE-2024-1",
  title: "XSS",
  cvssBase: 9.8,
  fixVersion: "18.2.1",
  riskScore: 98,
  riskLevel: "kritisch",
  description: "Beschreibung aus der OKF-Datei",
  rationale: "",
  references: [],
  sources: [],
  findings: [],
};

const IDLE_INGEST = {
  running: false,
  startedAt: null,
  finishedAt: null,
  componentsScanned: null,
  findingsFound: null,
  error: null,
};

const SECOND = { ...FINDING, advisoryId: "CVE-2024-2", cveId: "CVE-2024-2", riskLevel: "mittel" };

function bodyFor(url: URL): unknown {
  if (url.pathname === "/api/cves/CVE-2024-1") return DETAIL;
  if (url.pathname !== "/api/cves") return IDLE_INGEST;
  const all = [FINDING, SECOND];
  const severities = url.searchParams.getAll("severity");
  const items = severities.length ? all.filter((f) => severities.includes(f.riskLevel)) : all;
  return { items, total: items.length, unfilteredTotal: all.length };
}

const requests: string[] = [];

function mockApi() {
  requests.length = 0;
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = new URL(String(input), "http://localhost");
    requests.push(url.pathname + url.search);
    return Promise.resolve(new Response(JSON.stringify(bodyFor(url)), { status: 200 }));
  });
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("App", () => {
  it("filtert nur die Tabelle, Kacheln zeigen den Gesamtstand", async () => {
    mockApi();
    renderApp();

    await screen.findByTestId("cves-item-CVE-2024-2-1");
    await userEvent.click(screen.getByTestId("cves-select-severity-kritisch"));

    expect(await screen.findByTestId("cves-text-filter-summary")).toHaveTextContent("1 von 2");
    expect(screen.queryByTestId("cves-item-CVE-2024-2-1")).not.toBeInTheDocument();
    expect(screen.getByTestId("cves-list-kpis")).toHaveTextContent("2");
    expect(requests).toContain("/api/cves?severity=kritisch");
  });

  it("öffnet den CVE-Drawer per Klick auf eine Zeile", async () => {
    mockApi();
    renderApp();

    await userEvent.click(await screen.findByTestId("cves-item-CVE-2024-1-1"));

    expect(await screen.findByTestId("cves-text-detail-description")).toHaveTextContent(
      "Beschreibung aus der OKF-Datei",
    );
  });

  it("zeigt standardmaessig das Schwachstellen-Dashboard", () => {
    renderApp();

    expect(screen.getByTestId("app-text-title")).toHaveTextContent("Schwachstellen");
    expect(screen.getByTestId("cves-section-overview")).toBeInTheDocument();
  });

  it("wechselt ueber die Navigation zum Inventar", async () => {
    renderApp();

    await userEvent.click(screen.getByTestId("app-btn-nav-inventory"));

    expect(screen.getByTestId("inventory-section-manage")).toBeInTheDocument();
  });

  it("wechselt ueber die Navigation zu den Quellen", async () => {
    renderApp();

    await userEvent.click(screen.getByTestId("app-btn-nav-sources"));

    expect(screen.getByTestId("app-text-title")).toHaveTextContent("Quellen");
    expect(screen.getByTestId("sources-section-overview")).toBeInTheDocument();
  });

  it("schaltet das dunkle Design um", async () => {
    renderApp();

    await userEvent.click(screen.getByTestId("app-btn-theme-toggle"));

    expect(document.documentElement).toHaveClass("dark");
  });
});
