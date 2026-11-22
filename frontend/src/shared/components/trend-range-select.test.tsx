import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { TrendRangeSelect } from "./trend-range-select";

describe("TrendRangeSelect", () => {
  it("meldet die gewählte Wochenzahl", () => {
    const onChange = vi.fn();
    render(<TrendRangeSelect value={12} onChange={onChange} feature="cves" />);

    fireEvent.click(screen.getByTestId("cves-btn-trend-range-26"));

    expect(onChange).toHaveBeenCalledWith(26);
  });

  it("ignoriert Klick auf die bereits aktive Auswahl", () => {
    const onChange = vi.fn();
    render(<TrendRangeSelect value={12} onChange={onChange} feature="cves" />);

    fireEvent.click(screen.getByTestId("cves-btn-trend-range-12"));

    expect(onChange).not.toHaveBeenCalled();
  });
});
