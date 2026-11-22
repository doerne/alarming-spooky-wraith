import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { FindingTrend } from "@/shared/api/finding-trend";

import { TrendChart } from "./trend-chart";

const base: FindingTrend = {
  weeks: [{ weekStart: "2026-11-16", new: 3, closed: 5, openAtEnd: 42 }],
  openAtStart: 44,
  newTotal: 3,
  closedTotal: 5,
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

describe("TrendChart", () => {
  it("rendert das Diagramm bei Bewegung", () => {
    render(<TrendChart trend={base} feature="cves" />);

    expect(screen.getByTestId("cves-chart-trend")).toBeInTheDocument();
    expect(screen.queryByTestId("cves-text-trend-empty")).not.toBeInTheDocument();
  });

  it("zeigt einen Leerzustand ohne Bewegung", () => {
    const quiet = {
      ...base,
      weeks: [{ weekStart: "2026-11-16", new: 0, closed: 0, openAtEnd: 5 }],
    };
    render(<TrendChart trend={quiet} feature="cves" />);

    expect(screen.getByTestId("cves-text-trend-empty")).toHaveTextContent(
      "Im Zeitraum keine neuen oder erledigten Funde.",
    );
    expect(screen.queryByTestId("cves-chart-trend")).not.toBeInTheDocument();
  });
});
