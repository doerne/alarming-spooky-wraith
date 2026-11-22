import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { ApplicationFindingsPage } from "../api/inventory-api";
import { EMPTY_CVE_FILTERS } from "../model/cve-filters";
import { ApplicationCvesPanel } from "./application-cves-panel";

const emptyPage: ApplicationFindingsPage = { items: [], total: 0, unfilteredTotal: 0 };
const options = { advisories: [], components: [] };

function renderPanel(freshness: { text: string; warning: boolean } | undefined) {
  render(
    <ApplicationCvesPanel
      page={emptyPage}
      filters={EMPTY_CVE_FILTERS}
      options={options}
      freshness={freshness}
      onFiltersChange={vi.fn()}
      onSelectCve={vi.fn()}
    />,
  );
}

describe("ApplicationCvesPanel", () => {
  it("zeigt den Stand auch ohne Funde", () => {
    renderPanel({ text: "Noch nicht gescannt – Änderungen seit dem letzten Scan", warning: true });

    expect(screen.getByTestId("inventory-text-scan-freshness")).toHaveTextContent(
      "Noch nicht gescannt",
    );
    expect(screen.getByTestId("inventory-text-no-cves")).toBeInTheDocument();
  });

  it("zeigt ohne Stand keinen Hinweis", () => {
    renderPanel(undefined);

    expect(screen.queryByTestId("inventory-text-scan-freshness")).toBeNull();
  });
});
