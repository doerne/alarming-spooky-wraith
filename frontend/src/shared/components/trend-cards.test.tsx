import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { FindingTrend } from "@/shared/api/finding-trend";

import { TrendCards } from "./trend-cards";

const base: FindingTrend = {
  weeks: [],
  openAtStart: 44,
  newTotal: 7,
  closedTotal: 12,
  closedByOutcome: {
    fixed_confirmed: 0,
    fixed_reported: 0,
    fixed_manual: 0,
    accepted: 0,
    false_positive: 0,
  },
  untouchedNow: 30,
  inProgressNow: 12,
  openBySeverityNow: { kritisch: 3, hoch: 10, mittel: 20, niedrig: 9 },
};

describe("TrendCards", () => {
  it("zeigt Rückgang mit Minus und die Kennzahlen", () => {
    render(<TrendCards trend={base} feature="cves" />);

    expect(screen.getByTestId("cves-text-trend-open-delta")).toHaveTextContent("−2");
    expect(screen.getByTestId("cves-card-trend-open")).toHaveTextContent("42");
    expect(screen.getByTestId("cves-card-trend-untouched")).toHaveTextContent("30");
    expect(screen.getByTestId("cves-card-trend-in-progress")).toHaveTextContent("12");
    expect(screen.getByTestId("cves-card-trend-new")).toHaveTextContent("7");
    expect(screen.getByTestId("cves-card-trend-closed")).toHaveTextContent("12");
  });

  it("zeigt Anstieg mit Plus", () => {
    render(<TrendCards trend={{ ...base, openAtStart: 39 }} feature="cves" />);

    expect(screen.getByTestId("cves-text-trend-open-delta")).toHaveTextContent("+3");
  });

  it("zeigt Gleichstand als ±0", () => {
    render(<TrendCards trend={{ ...base, openAtStart: 42 }} feature="cves" />);

    expect(screen.getByTestId("cves-text-trend-open-delta")).toHaveTextContent("±0");
  });
});
