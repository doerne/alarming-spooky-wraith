import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { ScanStep, ScanStepState } from "@/shared/api/scan-status";

import { ScanProgress } from "./scan-progress";

const SOURCE_COUNT = 21;
const DONE_COUNT = 7;

function sourceState(index: number): ScanStepState {
  if (index < DONE_COUNT) return "done";
  if (index === DONE_COUNT) return "skipped";
  if (index === DONE_COUNT + 1) return "running";
  return "pending";
}

function steps(): ScanStep[] {
  const sources = Array.from({ length: SOURCE_COUNT }, (_, index) => ({
    key: `source-${index}`,
    label: `Quelle ${index}`,
    state: sourceState(index),
    detail: index === DONE_COUNT ? "API-Key fehlt" : "",
  }));
  return [
    ...sources,
    { key: "persist", label: "Funde speichern", state: "pending", detail: "" },
    { key: "github-sync", label: "GitHub-Abgleich", state: "pending", detail: "" },
  ];
}

describe("ScanProgress", () => {
  it("zählt erledigte Quellen ohne die Schlussschritte", () => {
    render(<ScanProgress steps={steps()} />);
    expect(screen.getByTestId("cves-text-scan-progress")).toHaveTextContent(
      "Scan läuft · 8 von 21 Quellen erledigt",
    );
  });

  it("zeigt den Anteil erledigter Schritte im Balken", () => {
    render(<ScanProgress steps={steps()} />);
    const bar = screen.getByRole("progressbar", { name: "Scan-Fortschritt" });
    expect(bar).toHaveAttribute("aria-valuenow", "35");
  });

  it("nennt bei übersprungenen Quellen den Grund", () => {
    render(<ScanProgress steps={steps()} />);
    expect(screen.getByTestId("cves-item-scan-step-source-7")).toHaveAttribute(
      "title",
      "API-Key fehlt",
    );
  });

  it("hebt fehlgeschlagene Schritte hervor", () => {
    const failed: ScanStep[] = [
      { key: "github-sync", label: "GitHub-Abgleich", state: "failed", detail: "" },
    ];
    render(<ScanProgress steps={failed} />);
    expect(screen.getByTestId("cves-item-scan-step-github-sync")).toHaveClass("text-destructive");
  });

  it("liest Zustand und Grund eines Schritts vor", () => {
    render(<ScanProgress steps={steps()} />);
    expect(screen.getByTestId("cves-item-scan-step-source-7")).toHaveTextContent(
      "übersprungen: API-Key fehlt",
    );
    expect(screen.getByTestId("cves-item-scan-step-source-8")).toHaveTextContent("läuft");
  });

  it("liest den Balken als Satz vor und listet die Schritte", () => {
    render(<ScanProgress steps={steps()} />);
    expect(screen.getByTestId("cves-card-scan-bar")).toHaveAttribute(
      "aria-valuetext",
      "8 von 21 Quellen erledigt",
    );
    expect(screen.getByTestId("cves-list-scan-steps").children).toHaveLength(23);
  });

  it("zeigt ohne Schritte 0 Prozent", () => {
    render(<ScanProgress steps={[]} />);
    expect(screen.getByTestId("cves-card-scan-bar")).toHaveAttribute("aria-valuenow", "0");
  });
});
