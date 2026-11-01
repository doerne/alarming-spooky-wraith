import { describe, expect, it } from "vitest";

import { applicationsOf } from "./filters";

describe("applicationsOf", () => {
  it("liefert jede Anwendung einmal, alphabetisch", () => {
    const findings = [
      { applicationId: 2, applicationName: "Shop" },
      { applicationId: 1, applicationName: "Blog" },
      { applicationId: 2, applicationName: "Shop" },
    ];
    expect(applicationsOf(findings)).toEqual([
      { id: 1, name: "Blog" },
      { id: 2, name: "Shop" },
    ]);
  });
});
