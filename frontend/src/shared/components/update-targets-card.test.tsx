import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { RemediationKpis } from "@/shared/api/remediation-kpis";

import { UpdateTargetsCard } from "./update-targets-card";

const updates: RemediationKpis["updates"] = {
  targets: [
    {
      packageName: "lodash",
      ecosystem: "npm",
      targetVersion: "4.17.21",
      findings: 3,
      applications: 2,
    },
    {
      packageName: "django",
      ecosystem: null,
      targetVersion: "5.0.1",
      findings: 1,
      applications: 1,
    },
  ],
  fixableOpen: 4,
  openTotal: 9,
  morePackages: 0,
};

describe("UpdateTargetsCard", () => {
  it("zeigt Zeilen und Behebbarkeits-Summe", () => {
    render(<UpdateTargetsCard updates={updates} feature="cves" showApplications />);

    expect(screen.getByTestId("cves-text-fixable")).toHaveTextContent(
      "4 von 9 offenen Funden durch Update behebbar",
    );
    expect(screen.getByTestId("cves-item-update-target-0")).toHaveTextContent("lodash");
    expect(screen.getByTestId("cves-item-update-target-0")).toHaveTextContent("4.17.21");
    expect(screen.getByTestId("cves-item-update-target-1")).toHaveTextContent("django");
  });

  it("zeigt die Spalte Anwendungen nur bei showApplications", () => {
    const { rerender } = render(
      <UpdateTargetsCard updates={updates} feature="cves" showApplications />,
    );
    expect(screen.getByTestId("cves-list-update-targets")).toHaveTextContent("Anwendungen");

    rerender(<UpdateTargetsCard updates={updates} feature="cves" showApplications={false} />);
    expect(screen.getByTestId("cves-list-update-targets")).not.toHaveTextContent("Anwendungen");
  });

  it("zeigt weitere Pakete", () => {
    render(
      <UpdateTargetsCard
        updates={{ ...updates, morePackages: 2 }}
        feature="cves"
        showApplications
      />,
    );

    expect(screen.getByTestId("cves-card-update-targets")).toHaveTextContent("+ 2 weitere Pakete");
  });

  it("zeigt ohne Ziele den Leerzustand", () => {
    render(
      <UpdateTargetsCard
        updates={{ ...updates, targets: [], fixableOpen: 0 }}
        feature="cves"
        showApplications
      />,
    );

    expect(screen.getByTestId("cves-card-update-targets")).toHaveTextContent(
      "Kein offener Fund mit bekannter Fix-Version.",
    );
    expect(screen.queryByTestId("cves-list-update-targets")).not.toBeInTheDocument();
  });
});
