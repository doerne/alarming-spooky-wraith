import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { ApplicationFinding } from "../model/types";
import { ApplicationCves } from "./application-cves";

const findings: ApplicationFinding[] = [
  {
    advisoryId: "CVE-2024-123",
    cveId: "CVE-2024-123",
    title: "XSS in react",
    componentName: "react",
    componentVersion: "18.2.0",
    riskScore: 98,
    riskLevel: "kritisch",
    fixVersion: "18.2.1",
    status: "offen",
  },
];

describe("ApplicationCves", () => {
  it("zeigt die Funde der Anwendung", () => {
    render(<ApplicationCves findings={findings} />);

    const row = screen.getByTestId("inventory-item-cve-CVE-2024-123");
    expect(row).toHaveTextContent("react");
    expect(row).toHaveTextContent("kritisch");
  });

  it("zeigt einen Hinweis, wenn keine Funde vorliegen", () => {
    render(<ApplicationCves findings={[]} />);

    expect(screen.getByTestId("inventory-text-no-cves")).toBeInTheDocument();
  });
});
