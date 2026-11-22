import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { RemediationKpis } from "@/shared/api/remediation-kpis";

import { DeadlineCard } from "./deadline-card";

const deadlines: RemediationKpis["deadlines"] = {
  overdue: 0,
  dueSoon: 4,
  overdueBySeverity: { kritisch: 0, hoch: 0, mittel: 0, niedrig: 0 },
  nextDueAt: "2026-12-05T00:00:00Z",
};

describe("DeadlineCard", () => {
  it("zeigt Kennzahlen und nächstes Fristdatum", () => {
    render(<DeadlineCard deadlines={deadlines} openTotal={10} feature="cves" />);

    expect(screen.getByTestId("cves-text-overdue")).toHaveTextContent("0");
    expect(screen.getByTestId("cves-text-overdue")).not.toHaveClass("text-destructive");
    expect(screen.getByTestId("cves-text-due-soon")).toHaveTextContent("4");
    expect(screen.getByTestId("cves-text-next-due")).toHaveTextContent(/\d{2}\.\d{2}\./);
  });

  it("rendert keine Klasse undefined", () => {
    render(<DeadlineCard deadlines={deadlines} openTotal={10} feature="cves" />);

    expect(screen.getByTestId("cves-text-due-soon").className).not.toContain("undefined");
    expect(screen.getByTestId("cves-text-overdue").className).not.toContain("undefined");
  });

  it("färbt Überfälliges mit text-destructive", () => {
    render(<DeadlineCard deadlines={{ ...deadlines, overdue: 2 }} openTotal={10} feature="cves" />);

    expect(screen.getByTestId("cves-text-overdue")).toHaveClass("text-destructive");
  });

  it("zeigt ohne offenen Bestand den Leerzustand", () => {
    render(
      <DeadlineCard
        deadlines={{ ...deadlines, dueSoon: 0, nextDueAt: null }}
        openTotal={0}
        feature="cves"
      />,
    );

    expect(screen.getByTestId("cves-card-deadlines")).toHaveTextContent("Keine offenen Funde.");
    expect(screen.queryByTestId("cves-text-overdue")).not.toBeInTheDocument();
  });
});
