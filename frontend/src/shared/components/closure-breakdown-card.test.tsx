import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { ClosedByOutcome } from "@/shared/api/finding-trend";

import { ClosureBreakdownCard } from "./closure-breakdown-card";

const outcome: ClosedByOutcome = {
  fixed_confirmed: 5,
  fixed_reported: 2,
  fixed_manual: 1,
  accepted: 3,
  false_positive: 0,
};

describe("ClosureBreakdownCard", () => {
  it("zeigt Zahlen und Bezeichnung je Art", () => {
    render(<ClosureBreakdownCard closedByOutcome={outcome} feature="cves" />);

    expect(screen.getByTestId("cves-item-closure-fixed-confirmed")).toHaveTextContent(
      "Behoben, bestätigt",
    );
    expect(screen.getByTestId("cves-item-closure-fixed-confirmed")).toHaveTextContent("5");
    expect(screen.getByTestId("cves-item-closure-accepted")).toHaveTextContent("Akzeptiert");
    expect(screen.getByTestId("cves-item-closure-false-positive")).toHaveTextContent(
      "False Positive",
    );
  });

  it("zeigt bei Summe 0 den Leerzustand", () => {
    const empty = {
      fixed_confirmed: 0,
      fixed_reported: 0,
      fixed_manual: 0,
      accepted: 0,
      false_positive: 0,
    };
    render(<ClosureBreakdownCard closedByOutcome={empty} feature="cves" />);

    expect(screen.getByTestId("cves-card-closure-breakdown")).toHaveTextContent(
      "Im Zeitraum nichts erledigt.",
    );
    expect(screen.queryByTestId("cves-item-closure-accepted")).not.toBeInTheDocument();
  });

  it("lässt Segmente mit 0 in der Leiste weg, die Legende behält alle fünf", () => {
    render(<ClosureBreakdownCard closedByOutcome={outcome} feature="cves" />);

    expect(screen.getAllByTestId(/^cves-item-closure-/)).toHaveLength(5);
    expect(screen.getAllByTestId(/^cves-segment-closure-/)).toHaveLength(4);
    expect(screen.queryByTestId("cves-segment-closure-false-positive")).not.toBeInTheDocument();
  });
});
