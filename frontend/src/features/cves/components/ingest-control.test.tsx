import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { ScanStatus } from "@/shared/api/scan-status";

import { IngestControl } from "./ingest-control";

const idle: ScanStatus = {
  running: false,
  startedAt: null,
  finishedAt: null,
  componentsScanned: null,
  findingsFound: null,
  error: null,
  lastRun: null,
  lastUsableRun: null,
  steps: [],
};

const fresh = { text: "Stand: heute 04:12", warning: false };

describe("IngestControl", () => {
  it("startet einen Scan", async () => {
    const onStart = vi.fn();
    render(
      <IngestControl state={idle} alreadyRunning={false} freshness={fresh} onStart={onStart} />,
    );

    await userEvent.click(screen.getByTestId("cves-btn-run-ingest"));

    expect(onStart).toHaveBeenCalled();
  });

  it("ist gesperrt, solange ein Scan läuft", () => {
    render(
      <IngestControl
        state={{ ...idle, running: true }}
        alreadyRunning={false}
        freshness={fresh}
        onStart={vi.fn()}
      />,
    );

    const button = screen.getByTestId("cves-btn-run-ingest");
    expect(button).toBeDisabled();
    expect(button).toHaveTextContent("Scan läuft");
  });

  it("zeigt den Fehler des letzten Laufs", () => {
    const failed = { ...idle, error: "Lauf fehlgeschlagen (DataError)" };
    render(
      <IngestControl state={failed} alreadyRunning={false} freshness={fresh} onStart={vi.fn()} />,
    );

    expect(screen.getByTestId("cves-error-ingest")).toHaveTextContent("DataError");
  });

  it("meldet einen bereits laufenden Scan", () => {
    render(<IngestControl state={idle} alreadyRunning freshness={fresh} onStart={vi.fn()} />);

    expect(screen.getByTestId("cves-text-ingest-running")).toHaveTextContent(
      "Ein Scan läuft bereits",
    );
  });

  it("zeigt, wie aktuell die Daten sind", () => {
    render(
      <IngestControl state={idle} alreadyRunning={false} freshness={fresh} onStart={vi.fn()} />,
    );

    expect(screen.getByTestId("cves-text-scan-freshness")).toHaveTextContent("Stand: heute 04:12");
    expect(screen.queryByTestId("cves-text-ingest-result")).toBeNull();
  });

  it("zeigt den Fortschritt nur, solange ein Scan läuft", () => {
    const step = { key: "osv", label: "OSV", state: "running" as const, detail: "" };
    const { rerender } = render(
      <IngestControl
        state={{ ...idle, running: true, steps: [step] }}
        alreadyRunning={false}
        freshness={fresh}
        onStart={vi.fn()}
      />,
    );
    expect(screen.getByTestId("cves-card-scan-progress")).toBeInTheDocument();

    rerender(
      <IngestControl
        state={{ ...idle, steps: [{ ...step, state: "done" }] }}
        alreadyRunning={false}
        freshness={fresh}
        onStart={vi.fn()}
      />,
    );
    expect(screen.queryByTestId("cves-card-scan-progress")).toBeNull();
  });

  it("zeigt keinen Fortschritt, solange das Backend keine Schritte meldet", () => {
    render(
      <IngestControl
        state={{ ...idle, running: true }}
        alreadyRunning={false}
        freshness={fresh}
        onStart={vi.fn()}
      />,
    );
    expect(screen.queryByTestId("cves-card-scan-progress")).toBeNull();
  });
});
