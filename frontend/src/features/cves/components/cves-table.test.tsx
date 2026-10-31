import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { Finding } from "../model/types";
import { CvesTable } from "./cves-table";

function finding(advisoryId: string, riskScore: number, riskLevel: Finding["riskLevel"]): Finding {
  return {
    advisoryId,
    cveId: advisoryId,
    title: `t ${advisoryId}`,
    applicationName: "Shop",
    componentName: "react",
    componentVersion: "18.2.0",
    ecosystem: "npm",
    riskScore,
    riskLevel,
    fixVersion: "18.2.1",
    status: "offen",
  };
}

describe("CvesTable", () => {
  const findings = [finding("CVE-2024-1", 98, "kritisch"), finding("CVE-2024-2", 50, "mittel")];

  it("rendert eine Zeile je Fund in der uebergebenen Reihenfolge", () => {
    render(<CvesTable findings={findings} />);

    const rows = screen.getAllByTestId(/^cves-item-/);
    expect(rows.map((row) => row.getAttribute("data-testid"))).toEqual([
      "cves-item-CVE-2024-1",
      "cves-item-CVE-2024-2",
    ]);
  });

  it("zeigt die Risikostufe als Badge", () => {
    render(<CvesTable findings={findings} />);

    expect(screen.getByTestId("cves-item-CVE-2024-1")).toHaveTextContent("kritisch");
  });
});
