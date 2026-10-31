import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SectionCards } from "./section-cards";

describe("SectionCards", () => {
  it("zeigt die vier Kennzahlen mit Werten", () => {
    render(<SectionCards kpis={{ total: 7, kritisch: 2, hoch: 3, offen: 4 }} />);

    expect(screen.getByTestId("cves-card-kpi-total")).toHaveTextContent("7");
    expect(screen.getByTestId("cves-card-kpi-kritisch")).toHaveTextContent("Kritisch");
    expect(screen.getByTestId("cves-card-kpi-kritisch")).toHaveTextContent("2");
    expect(screen.getByTestId("cves-card-kpi-hoch")).toHaveTextContent("3");
    expect(screen.getByTestId("cves-card-kpi-offen")).toHaveTextContent("4");
  });
});
