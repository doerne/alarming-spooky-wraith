import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CvesExportButton } from "./cves-export-button";

describe("CvesExportButton", () => {
  it("verlinkt den Markdown-Export der Anwendung als Download", () => {
    render(<CvesExportButton applicationId={4} />);

    const link = screen.getByTestId("inventory-link-cves-export");
    expect(link).toHaveAttribute("href", "/api/applications/4/cves/export");
    expect(link).toHaveAttribute("download");
    expect(link).toHaveTextContent("Für KI exportieren");
  });
});
