import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { FilterSummary } from "./filter-summary";

describe("FilterSummary", () => {
  it("zeigt N von M und setzt zurück", async () => {
    const onReset = vi.fn();
    render(<FilterSummary shown={12} total={83} active onReset={onReset} />);

    expect(screen.getByTestId("cves-text-filter-summary")).toHaveTextContent("12 von 83 Funden");
    await userEvent.click(screen.getByTestId("cves-btn-reset-filters"));
    expect(onReset).toHaveBeenCalled();
  });

  it("sperrt Zurücksetzen ohne aktive Filter", () => {
    render(<FilterSummary shown={83} total={83} active={false} onReset={vi.fn()} />);

    expect(screen.getByTestId("cves-btn-reset-filters")).toBeDisabled();
  });
});
