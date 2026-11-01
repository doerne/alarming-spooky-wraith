import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { SafeLink } from "./safe-link";

describe("SafeLink", () => {
  it("rendert http(s) als externen Link", () => {
    render(<SafeLink href="https://nvd.nist.gov/x" testId="cves-link-detail-test" />);

    const link = screen.getByTestId("cves-link-detail-test");
    expect(link.tagName).toBe("A");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noreferrer");
    expect(link).toHaveTextContent("https://nvd.nist.gov/x");
  });

  it("rendert andere Schemata nur als Text", () => {
    render(<SafeLink href="javascript:alert(1)" testId="cves-link-detail-test" />);

    const element = screen.getByTestId("cves-link-detail-test");
    expect(element.tagName).toBe("SPAN");
    expect(element).not.toHaveAttribute("href");
  });
});
