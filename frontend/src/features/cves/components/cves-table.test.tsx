import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { EMPTY_FILTERS, type FindingFilters } from "../model/filters";
import type { Finding } from "../model/types";
import { CvesTable } from "./cves-table";

function finding(
  advisoryId: string,
  riskScore: number,
  riskLevel: Finding["riskLevel"],
  componentId = 1,
): Finding {
  return {
    advisoryId,
    cveId: advisoryId,
    title: `t ${advisoryId}`,
    applicationId: 1,
    applicationName: "Shop",
    componentId,
    componentName: "react",
    componentVersion: "18.2.0",
    ecosystem: "npm",
    riskScore,
    riskLevel,
    fixVersion: "18.2.1",
    status: "offen",
  };
}

interface RenderOptions {
  filters?: FindingFilters;
  onSelect?: (advisoryId: string) => void;
}

function renderTable(rows: Finding[], options: RenderOptions = {}) {
  const onFiltersChange = vi.fn();
  const onReset = vi.fn();
  render(
    <CvesTable
      findings={rows}
      filters={options.filters ?? EMPTY_FILTERS}
      applications={[{ id: 1, name: "Shop" }]}
      onFiltersChange={onFiltersChange}
      onReset={onReset}
      onSelect={options.onSelect ?? vi.fn()}
    />,
  );
  return { onFiltersChange, onReset };
}

describe("CvesTable", () => {
  const findings = [finding("CVE-2024-1", 98, "kritisch"), finding("CVE-2024-2", 50, "mittel")];

  it("rendert eine Zeile je Fund in der uebergebenen Reihenfolge", () => {
    renderTable(findings);

    const rows = screen.getAllByTestId(/^cves-item-/);
    expect(rows.map((row) => row.getAttribute("data-testid"))).toEqual([
      "cves-item-CVE-2024-1-1",
      "cves-item-CVE-2024-2-1",
    ]);
  });

  it("zeigt die Risikostufe als Badge", () => {
    renderTable(findings);

    expect(screen.getByTestId("cves-item-CVE-2024-1-1")).toHaveTextContent("kritisch");
  });

  it("öffnet per Klick", async () => {
    const onSelect = vi.fn();
    renderTable(findings, { onSelect });

    await userEvent.click(screen.getByTestId("cves-item-CVE-2024-2-1"));

    expect(onSelect).toHaveBeenCalledWith("CVE-2024-2");
  });

  it("öffnet per Enter", async () => {
    const onSelect = vi.fn();
    renderTable(findings, { onSelect });

    screen.getByTestId("cves-item-CVE-2024-1-1").focus();
    await userEvent.keyboard("{Enter}");

    expect(onSelect).toHaveBeenCalledWith("CVE-2024-1");
  });

  it("vergibt eindeutige Zeilen-IDs, wenn eine CVE zwei Komponenten betrifft", () => {
    const twice = [
      finding("CVE-2024-1", 98, "kritisch", 1),
      finding("CVE-2024-1", 98, "kritisch", 2),
    ];
    renderTable(twice);

    expect(screen.getByTestId("cves-item-CVE-2024-1-1")).toBeInTheDocument();
    expect(screen.getByTestId("cves-item-CVE-2024-1-2")).toBeInTheDocument();
  });

  it("zeigt das Ökosystem als eigene Spalte", () => {
    renderTable(findings);

    expect(screen.getByTestId("cves-item-CVE-2024-1-1")).toHaveTextContent("npm");
  });

  it("filtert über den Spaltenkopf Risiko", async () => {
    const { onFiltersChange } = renderTable(findings);

    await userEvent.click(screen.getByTestId("cves-select-severity"));
    await userEvent.click(screen.getByTestId("cves-select-severity-option-kritisch"));

    expect(onFiltersChange).toHaveBeenCalledWith({ ...EMPTY_FILTERS, severities: ["kritisch"] });
  });

  it("filtert über die Suchfelder im Kopf", async () => {
    const { onFiltersChange } = renderTable(findings);

    await userEvent.type(screen.getByTestId("cves-input-filter-component"), "d");
    await userEvent.type(screen.getByTestId("cves-input-filter-advisory"), "x");

    expect(onFiltersChange).toHaveBeenCalledWith({ ...EMPTY_FILTERS, componentQuery: "d" });
    expect(onFiltersChange).toHaveBeenCalledWith({ ...EMPTY_FILTERS, advisoryQuery: "x" });
  });

  it("bietet Anwendung, Ökosystem und Status als Kopf-Filter", () => {
    renderTable(findings);

    expect(screen.getByTestId("cves-select-application")).toBeInTheDocument();
    expect(screen.getByTestId("cves-select-ecosystem")).toBeInTheDocument();
    expect(screen.getByTestId("cves-select-status")).toBeInTheDocument();
  });

  it("zeigt bei 0 Treffern eine Zeile mit Zurücksetzen, Kopf bleibt", async () => {
    const { onReset } = renderTable([], { filters: { ...EMPTY_FILTERS, severities: ["niedrig"] } });

    expect(screen.getByTestId("cves-select-severity")).toBeInTheDocument();
    expect(screen.getByTestId("cves-text-no-results")).toHaveTextContent(
      "Keine Funde für diese Filter",
    );
    await userEvent.click(screen.getByTestId("cves-btn-reset-no-results"));
    expect(onReset).toHaveBeenCalled();
  });
});
