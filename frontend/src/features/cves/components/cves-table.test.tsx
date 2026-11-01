import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { Finding } from "../model/types";
import { CvesTable } from "./cves-table";

function finding(
  advisoryId: string,
  riskScore: number,
  riskLevel: Finding["riskLevel"],
  componentId = 1,
): Finding {
  return {
    advisoryId,
    cveId: advisoryId,
    title: `t ${advisoryId}`,
    applicationName: "Shop",
    componentId,
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
    render(<CvesTable findings={findings} onSelect={vi.fn()} />);

    const rows = screen.getAllByTestId(/^cves-item-/);
    expect(rows.map((row) => row.getAttribute("data-testid"))).toEqual([
      "cves-item-CVE-2024-1-1",
      "cves-item-CVE-2024-2-1",
    ]);
  });

  it("zeigt die Risikostufe als Badge", () => {
    render(<CvesTable findings={findings} onSelect={vi.fn()} />);

    expect(screen.getByTestId("cves-item-CVE-2024-1-1")).toHaveTextContent("kritisch");
  });

  it("öffnet per Klick", async () => {
    const onSelect = vi.fn();
    render(<CvesTable findings={findings} onSelect={onSelect} />);

    await userEvent.click(screen.getByTestId("cves-item-CVE-2024-2-1"));

    expect(onSelect).toHaveBeenCalledWith("CVE-2024-2");
  });

  it("öffnet per Enter", async () => {
    const onSelect = vi.fn();
    render(<CvesTable findings={findings} onSelect={onSelect} />);

    screen.getByTestId("cves-item-CVE-2024-1-1").focus();
    await userEvent.keyboard("{Enter}");

    expect(onSelect).toHaveBeenCalledWith("CVE-2024-1");
  });

  it("vergibt eindeutige Zeilen-IDs, wenn eine CVE zwei Komponenten betrifft", () => {
    const twice = [
      finding("CVE-2024-1", 98, "kritisch", 1),
      finding("CVE-2024-1", 98, "kritisch", 2),
    ];
    render(<CvesTable findings={twice} onSelect={vi.fn()} />);

    expect(screen.getByTestId("cves-item-CVE-2024-1-1")).toBeInTheDocument();
    expect(screen.getByTestId("cves-item-CVE-2024-1-2")).toBeInTheDocument();
  });
});
