import { describe, expect, it } from "vitest";

import { advisoryOptionsOf, applicationsOf, columnOptionsOf, componentOptionsOf } from "./filters";

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

describe("advisoryOptionsOf / componentOptionsOf", () => {
  const findings = [
    { advisoryId: "GHSA-b", cveId: null, componentName: "react" },
    { advisoryId: "CVE-2024-2", cveId: "CVE-2024-2", componentName: "django" },
    { advisoryId: "CVE-2024-2", cveId: "CVE-2024-2", componentName: "react" },
  ];

  it("liefert jede Advisory einmal, sortiert, Label = CVE-ID oder eigene ID", () => {
    expect(advisoryOptionsOf(findings)).toEqual([
      { value: "CVE-2024-2", label: "CVE-2024-2" },
      { value: "GHSA-b", label: "GHSA-b" },
    ]);
  });

  it("liefert jede Komponente einmal, alphabetisch", () => {
    expect(componentOptionsOf(findings)).toEqual([
      { value: "django", label: "django" },
      { value: "react", label: "react" },
    ]);
  });
});

describe("columnOptionsOf", () => {
  it("baut Anwendungs-, Advisory- und Komponenten-Optionen aus den Funden", () => {
    const options = columnOptionsOf([
      {
        applicationId: 2,
        applicationName: "Shop",
        advisoryId: "CVE-1",
        cveId: "CVE-1",
        componentName: "react",
      },
      {
        applicationId: 1,
        applicationName: "Blog",
        advisoryId: "GHSA-x",
        cveId: null,
        componentName: "django",
      },
    ]);
    expect(options.applications).toEqual([
      { value: "1", label: "Blog" },
      { value: "2", label: "Shop" },
    ]);
    expect(options.advisories.map((option) => option.value)).toEqual(["CVE-1", "GHSA-x"]);
    expect(options.components.map((option) => option.value)).toEqual(["django", "react"]);
  });
});
