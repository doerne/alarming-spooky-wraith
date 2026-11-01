import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { EMPTY_FILTERS } from "../model/filters";
import { FilterSummary } from "./filter-summary";
import { FindingsFilterBar } from "./findings-filter-bar";

const APPS = [
  { id: 1, name: "Shop" },
  { id: 2, name: "Blog" },
];

function renderBar(filters = EMPTY_FILTERS) {
  const onChange = vi.fn();
  const onReset = vi.fn();
  render(
    <FindingsFilterBar
      filters={filters}
      applications={APPS}
      onChange={onChange}
      onReset={onReset}
    />,
  );
  return { onChange, onReset };
}

describe("FindingsFilterBar", () => {
  it("meldet den gewählten Schweregrad", async () => {
    const { onChange } = renderBar();

    await userEvent.click(screen.getByTestId("cves-select-severity-kritisch"));

    expect(onChange).toHaveBeenCalledWith({ ...EMPTY_FILTERS, severities: ["kritisch"] });
  });

  it("meldet Status, Ökosystem und Anwendung", async () => {
    const { onChange } = renderBar();

    await userEvent.click(screen.getByTestId("cves-select-status-false_positive"));
    await userEvent.click(screen.getByTestId("cves-select-ecosystem-none"));
    await userEvent.selectOptions(screen.getByTestId("cves-select-application"), "2");

    expect(onChange).toHaveBeenCalledWith({ ...EMPTY_FILTERS, statuses: ["false_positive"] });
    expect(onChange).toHaveBeenCalledWith({ ...EMPTY_FILTERS, ecosystems: ["none"] });
    expect(onChange).toHaveBeenCalledWith({ ...EMPTY_FILTERS, applicationId: 2 });
  });

  it("meldet den Suchtext", async () => {
    const { onChange } = renderBar();

    await userEvent.type(screen.getByTestId("cves-input-search"), "x");

    expect(onChange).toHaveBeenCalledWith({ ...EMPTY_FILTERS, query: "x" });
  });

  it("setzt zurück", async () => {
    const { onReset } = renderBar({ ...EMPTY_FILTERS, query: "react" });

    await userEvent.click(screen.getByTestId("cves-btn-reset-filters"));

    expect(onReset).toHaveBeenCalled();
  });

  it("blendet den Anwendungsfilter ohne Anwendungen aus", () => {
    render(
      <FindingsFilterBar
        filters={EMPTY_FILTERS}
        applications={[]}
        onChange={vi.fn()}
        onReset={vi.fn()}
      />,
    );

    expect(screen.queryByTestId("cves-select-application")).not.toBeInTheDocument();
  });
});

describe("FilterSummary", () => {
  it("zeigt N von M", () => {
    render(<FilterSummary shown={12} total={83} />);

    expect(screen.getByTestId("cves-text-filter-summary")).toHaveTextContent("12 von 83 Funden");
  });

  it("zeigt leeren Zustand", () => {
    render(<FilterSummary shown={0} total={83} />);

    expect(screen.getByTestId("cves-text-no-results")).toHaveTextContent(
      "Keine Funde für diese Filter",
    );
  });
});
