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
  riskScore: 98,
  riskLevel: "kritisch",
  fixVersion: null,
  status: "offen",
};

function mockFindings(byApp: Record<string, (typeof FINDING)[]>) {
  vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = new URL(String(input), "http://localhost");
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
  it("zeigt ohne Funde nur den Hinweis, keine Filter", async () => {
    mockFindings({});
    renderPage(1);

    expect(await screen.findByTestId("inventory-text-no-cves")).toBeInTheDocument();
    expect(screen.queryByTestId("inventory-form-cve-filters")).not.toBeInTheDocument();
  });

  it("blendet die Tabelle aus, wenn Filter nichts finden", async () => {
    mockFindings({ "1": [FINDING] });
    renderPage(1);

    await screen.findByTestId("inventory-item-cve-CVE-2024-1-1");
    await userEvent.click(screen.getByTestId("inventory-select-severity-niedrig"));

    expect(await screen.findByTestId("inventory-text-no-results")).toBeInTheDocument();
    expect(screen.queryByTestId("inventory-list-cves")).not.toBeInTheDocument();
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
