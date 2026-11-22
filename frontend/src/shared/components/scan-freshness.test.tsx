import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ScanFreshness } from "./scan-freshness";

describe("ScanFreshness", () => {
  it("zeigt den Stand neutral an", () => {
    render(
      <ScanFreshness text="Stand: heute 04:12" warning={false} testId="cves-text-scan-freshness" />,
    );

    const element = screen.getByTestId("cves-text-scan-freshness");
    expect(element).toHaveTextContent("Stand: heute 04:12");
    expect(element.querySelector("svg")).toBeNull();
  });

  it("hebt eine Warnung mit Symbol hervor", () => {
    render(
      <ScanFreshness
        text="Stand: 20.11. 04:09 · älter als ein Tag"
        warning
        testId="cves-text-scan-freshness"
      />,
    );

    const element = screen.getByTestId("cves-text-scan-freshness");
    expect(element).toHaveTextContent("älter als ein Tag");
    expect(element.querySelector("svg")).not.toBeNull();
  });
});
