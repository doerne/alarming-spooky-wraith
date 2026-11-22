import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { DEFAULT_OVERVIEW_SORT } from "../model/overview";
import { overviewRow } from "./overview-fixtures";
import { OverviewTable } from "./overview-table";

const NOW = new Date("2026-12-10T10:00:00Z");

function renderTable(overrides: Partial<Parameters<typeof OverviewTable>[0]> = {}) {
  const props = {
    rows: [overviewRow()],
    sort: DEFAULT_OVERVIEW_SORT,
    now: NOW,
    onSort: vi.fn(),
    onSelect: vi.fn(),
    ...overrides,
  };
  render(<OverviewTable {...props} />);
  return props;
}

describe("OverviewTable", () => {
  it("zeigt die Kennzahlen einer Anwendung", () => {
    renderTable();
    const row = screen.getByTestId("inventory-item-app-1");
    expect(row).toHaveTextContent("Shop");
    expect(row).toHaveTextContent("Online-Shop");
    expect(row).toHaveTextContent("412");
    expect(row).toHaveTextContent("vor 2 Tagen");
    expect(row).toHaveTextContent("aktuell");
    expect(row).toHaveTextContent("acme/shop");
  });

  it("zeigt fehlende Werte", () => {
    renderTable({
      rows: [
        overviewRow({
          openBySeverity: { kritisch: 0, hoch: 0, mittel: 0, niedrig: 0 },
          latestSbomUploadAt: null,
          sbomStale: true,
          scanState: "never_scanned",
          githubRepository: null,
        }),
      ],
    });
    const row = screen.getByTestId("inventory-item-app-1");
    expect(row).toHaveTextContent("keine");
    expect(row).toHaveTextContent("keine SBOM");
    expect(row).toHaveTextContent("Noch kein Scan");
    expect(row).toHaveTextContent("–");
  });

  it("nennt das Änderungsdatum, wenn seit dem Scan geändert wurde", () => {
    renderTable({
      rows: [
        overviewRow({
          scanState: "changed_since_scan",
          inventoryChangedAt: "2026-12-03T09:00:00Z",
        }),
      ],
    });
    expect(screen.getByTestId("inventory-item-app-1")).toHaveTextContent("seit 03.12. geändert");
  });

  it("sortiert per Klick auf den Spaltenkopf", async () => {
    const props = renderTable({ sort: { key: "overdue", direction: "desc" } });
    await userEvent.click(screen.getByTestId("inventory-btn-sort-overdue"));
    expect(props.onSort).toHaveBeenCalledWith("overdue");
    expect(screen.getByTestId("inventory-btn-sort-overdue").closest("th")).toHaveAttribute(
      "aria-sort",
      "descending",
    );
  });

  it("öffnet die Anwendung per Klick auf die Zeile", async () => {
    const props = renderTable();
    await userEvent.click(screen.getByTestId("inventory-item-app-1"));
    expect(props.onSelect).toHaveBeenCalledWith(1);
  });

  it("zeigt die offenen Funde je Schweregrad", () => {
    renderTable();
    expect(screen.getByTestId("inventory-badge-open-kritisch-1")).toHaveTextContent("2");
    expect(screen.getByTestId("inventory-badge-open-hoch-1")).toHaveTextContent("1");
  });

  it("warnt bei veralteter SBOM mit Icon", () => {
    renderTable({
      rows: [overviewRow({ latestSbomUploadAt: "2026-10-01T10:00:00Z", sbomStale: true })],
    });
    const cell = screen.getByTestId("inventory-text-sbom-1");
    expect(cell).toHaveTextContent("vor 70 Tagen");
    expect(cell.querySelector("svg")).not.toBeNull();
  });

  it("warnt ohne Datum, wenn seit dem Scan geändert wurde", () => {
    renderTable({
      rows: [overviewRow({ scanState: "changed_since_scan", inventoryChangedAt: null })],
    });
    expect(screen.getByTestId("inventory-item-app-1")).toHaveTextContent(
      "Seit Änderung nicht gescannt",
    );
  });

  it("hat einen zugänglichen Namen", () => {
    renderTable();
    expect(screen.getByRole("table", { name: "Anwendungen" })).toBeInTheDocument();
  });
});
