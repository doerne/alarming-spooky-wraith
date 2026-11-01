import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { IngestState } from "../model/types";
import { IngestControl } from "./ingest-control";

const idle: IngestState = {
  running: false,
  startedAt: null,
  finishedAt: null,
  componentsScanned: null,
  findingsFound: null,
  error: null,
};

describe("IngestControl", () => {
  it("startet einen Scan", async () => {
    const onStart = vi.fn();
    render(<IngestControl state={idle} alreadyRunning={false} onStart={onStart} />);

    await userEvent.click(screen.getByTestId("cves-btn-run-ingest"));

    expect(onStart).toHaveBeenCalled();
  });

  it("ist gesperrt, solange ein Scan läuft", () => {
    render(
      <IngestControl state={{ ...idle, running: true }} alreadyRunning={false} onStart={vi.fn()} />,
    );

    const button = screen.getByTestId("cves-btn-run-ingest");
    expect(button).toBeDisabled();
    expect(button).toHaveTextContent("Scan läuft");
  });

  it("zeigt den Fehler des letzten Laufs", () => {
    const failed = { ...idle, error: "Lauf fehlgeschlagen (DataError)" };
    render(<IngestControl state={failed} alreadyRunning={false} onStart={vi.fn()} />);

    expect(screen.getByTestId("cves-error-ingest")).toHaveTextContent("DataError");
  });

  it("meldet einen bereits laufenden Scan", () => {
    render(<IngestControl state={idle} alreadyRunning onStart={vi.fn()} />);

    expect(screen.getByTestId("cves-text-ingest-running")).toHaveTextContent(
      "Ein Scan läuft bereits",
    );
  });

  it("zeigt das Ergebnis des letzten Laufs", () => {
    const done = { ...idle, finishedAt: "2026-11-01T12:00:00Z", findingsFound: 83 };
    render(<IngestControl state={done} alreadyRunning={false} onStart={vi.fn()} />);

    expect(screen.getByTestId("cves-text-ingest-result")).toHaveTextContent("83 Funde");
  });
});
