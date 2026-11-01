import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { ApplicationFinding } from "../model/types";
import { ApplicationCves } from "./application-cves";

const findings: ApplicationFinding[] = [
  {
    advisoryId: "CVE-2024-123",
    cveId: "CVE-2024-123",
    title: "XSS in react",
    componentId: 3,
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
    render(<ApplicationCves findings={findings} onSelect={vi.fn()} />);

    const row = screen.getByTestId("inventory-item-cve-CVE-2024-123-3");
    expect(row).toHaveTextContent("react");
    expect(row).toHaveTextContent("kritisch");
  });

  it("zeigt einen Hinweis, wenn keine Funde vorliegen", () => {
    render(<ApplicationCves findings={[]} onSelect={vi.fn()} />);

    expect(screen.getByTestId("inventory-text-no-cves")).toBeInTheDocument();
  });

  it("meldet die Auswahl einer CVE", async () => {
    const onSelect = vi.fn();
    render(<ApplicationCves findings={findings} onSelect={onSelect} />);

    await userEvent.click(screen.getByTestId("inventory-item-cve-CVE-2024-123-3"));

    expect(onSelect).toHaveBeenCalledWith("CVE-2024-123");
  });
});
