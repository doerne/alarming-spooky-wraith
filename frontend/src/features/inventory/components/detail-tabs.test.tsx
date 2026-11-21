import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { DetailTabs } from "./detail-tabs";

describe("DetailTabs", () => {
  it("zeigt im Reiter SBOMs das übergebene Panel", async () => {
    render(
      <DetailTabs
        components={[]}
        sbomNames={new Map()}
        cvesPanel={<p>CVE-Panel</p>}
        sbomsPanel={<p data-testid="inventory-text-test-sboms">SBOM-Panel</p>}
        editing={null}
        isSubmitting={false}
        onEdit={vi.fn()}
        onSubmitComponent={vi.fn()}
        onCancelEdit={vi.fn()}
      />,
    );

    expect(screen.queryByTestId("inventory-text-test-sboms")).not.toBeInTheDocument();
    await userEvent.click(screen.getByTestId("inventory-tab-sboms"));
    expect(screen.getByTestId("inventory-text-test-sboms")).toHaveTextContent("SBOM-Panel");
  });
});
