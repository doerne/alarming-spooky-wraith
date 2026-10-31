import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { SeverityCount } from "../model/stats";
import { SeverityChart } from "./severity-chart";

const data: SeverityCount[] = [
  { level: "kritisch", label: "Kritisch", count: 2 },
  { level: "hoch", label: "Hoch", count: 1 },
  { level: "mittel", label: "Mittel", count: 0 },
  { level: "niedrig", label: "Niedrig", count: 3 },
];

describe("SeverityChart", () => {
  it("rendert die Diagramm-Karte mit Titel", () => {
    render(<SeverityChart data={data} />);

    const card = screen.getByTestId("cves-card-severity-chart");
    expect(card).toBeInTheDocument();
    expect(card).toHaveTextContent("Funde nach Schweregrad");
  });
});
