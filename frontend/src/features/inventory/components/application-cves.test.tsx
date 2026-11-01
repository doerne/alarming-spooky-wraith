import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { type CveFilters, EMPTY_CVE_FILTERS } from "../model/cve-filters";
import type { ApplicationFinding } from "../model/types";
import { ApplicationCves } from "./application-cves";

const findings: ApplicationFinding[] = [
  {
    advisoryId: "CVE-2024-123",
    cveId: "CVE-2024-123",
    title: "XSS in react",
    componentId: 3,
    componentName: "react",
    componentVersion: "18.2.0",
    ecosystem: "npm",
    riskScore: 98,
    riskLevel: "kritisch",
    fixVersion: "18.2.1",
    status: "offen",
  },
];

function renderTable(rows = findings, filters: CveFilters = EMPTY_CVE_FILTERS) {
  const props = { onFiltersChange: vi.fn(), onReset: vi.fn(), onSelect: vi.fn() };
  const options = {
    advisories: [{ value: "CVE-2024-123", label: "CVE-2024-123" }],
    components: [{ value: "react", label: "react" }],
  };
  render(<ApplicationCves findings={rows} filters={filters} options={options} {...props} />);
  return props;
}

describe("ApplicationCves", () => {
  it("zeigt die Funde mit Ökosystem-Spalte", () => {
    renderTable();

    const row = screen.getByTestId("inventory-item-cve-CVE-2024-123-3");
    expect(row).toHaveTextContent("react");
    expect(row).toHaveTextContent("kritisch");
    expect(row).toHaveTextContent("npm");
  });

  it("meldet die Auswahl einer CVE", async () => {
    const { onSelect } = renderTable();

    await userEvent.click(screen.getByTestId("inventory-item-cve-CVE-2024-123-3"));

    expect(onSelect).toHaveBeenCalledWith("CVE-2024-123");
  });

  it("filtert über Spaltenköpfe ohne Anwendungsfilter", async () => {
    const { onFiltersChange } = renderTable();

    await userEvent.click(screen.getByTestId("inventory-select-status"));
    await userEvent.click(screen.getByTestId("inventory-checkbox-status-offen"));
    await userEvent.keyboard("{Escape}");
    await userEvent.click(screen.getByTestId("inventory-select-component"));
    await userEvent.click(screen.getByTestId("inventory-checkbox-component-react"));

    expect(onFiltersChange).toHaveBeenCalledWith({ ...EMPTY_CVE_FILTERS, statuses: ["offen"] });
    expect(onFiltersChange).toHaveBeenCalledWith({
      ...EMPTY_CVE_FILTERS,
      componentNames: ["react"],
    });
    expect(screen.queryByTestId("inventory-select-application")).not.toBeInTheDocument();
  });

  it("zeigt bei 0 Treffern eine Zeile mit Zurücksetzen", async () => {
    const { onReset } = renderTable([], { ...EMPTY_CVE_FILTERS, severities: ["niedrig"] });

    expect(screen.getByTestId("inventory-select-severity")).toBeInTheDocument();
    await userEvent.click(screen.getByTestId("inventory-btn-reset-no-results"));
    expect(onReset).toHaveBeenCalled();
  });
});
